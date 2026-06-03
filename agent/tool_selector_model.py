"""
Multi-Class Semantic Matching Engine
=====================================
A 3-stage hybrid pipeline for matching user queries to one of N class descriptions.

Stage 1 — Lexical     : TF-IDF cosine similarity (token overlap, n-grams)
Stage 2 — Semantic    : Sentence-BERT bi-encoder (dense vector similarity)
Stage 3 — Contextual  : Cross-encoder re-ranking (deep query-description interaction)

Final score = weighted sum of all three stages.

Install dependencies:
    pip install sentence-transformers scikit-learn numpy transformers torch
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, CrossEncoder


# ─────────────────────────────────────────────────────────────────────────────
# Core Engine
# ─────────────────────────────────────────────────────────────────────────────

class SemanticMatcher:
    """
    Matches a free-text query to one of N predefined class descriptions
    using a 3-stage hybrid scoring pipeline.

    Parameters
    ----------
    class_descriptions : dict[str, str]
        Mapping of {class_label: description_text}.
        Example: {"billing": "Questions about invoices, payments, refunds..."}

    bi_encoder_model : str
        HuggingFace model name for dense embeddings.
        Recommended options (ascending quality/cost):
          - "all-MiniLM-L6-v2"         (fast, good quality, 80MB)
          - "all-mpnet-base-v2"         (balanced, best general quality, 420MB)
          - "multi-qa-mpnet-base-dot-v1"(tuned for Q&A matching)

    cross_encoder_model : str
        HuggingFace model name for re-ranking.
        Recommended options:
          - "cross-encoder/ms-marco-MiniLM-L-6-v2"  (fast, good)
          - "cross-encoder/stsb-roberta-large"       (slower, more precise)

    weights : tuple[float, float, float]
        Blend weights for (lexical, semantic, contextual).
        Must sum to 1.0.
        Default (0.15, 0.50, 0.35) works well for most cases.
        Increase lexical weight if class names appear verbatim in queries.
        Increase contextual weight if you need highest accuracy (slower).

    top_k_rerank : int
        How many top candidates from the bi-encoder pass to the cross-encoder.
        Keep at 3–5; no need to cross-encode all classes unless N > 20.
    """

    def __init__(
        self,
        class_descriptions: dict[str, str],
        bi_encoder_model: str = "all-MiniLM-L6-v2",
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        weights: tuple[float, float, float] = (0.15, 0.50, 0.35),
        top_k_rerank: int = 3,
    ):
        assert abs(sum(weights) - 1.0) < 1e-6, "Weights must sum to 1.0"
        assert top_k_rerank <= len(class_descriptions), "top_k_rerank > number of classes"

        self.classes       = list(class_descriptions.keys())
        self.descriptions  = list(class_descriptions.values())
        self.weights       = weights
        self.top_k_rerank  = top_k_rerank

        print("[1/3] Loading bi-encoder (sentence-transformers)...")
        self.bi_encoder = SentenceTransformer(bi_encoder_model)
        # Pre-compute description embeddings once — reused for every query
        self.desc_embeddings = self.bi_encoder.encode(
            self.descriptions, convert_to_numpy=True, show_progress_bar=False
        )

        print("[2/3] Loading cross-encoder (re-ranker)...")
        self.cross_encoder = CrossEncoder(cross_encoder_model)

        print("[3/3] Fitting TF-IDF vectorizer...")
        self.tfidf = TfidfVectorizer(
            ngram_range=(1, 2),   # unigrams + bigrams
            sublinear_tf=True,    # log-scale term frequencies
            min_df=1,
            analyzer="word",
            stop_words="english",
        )
        self.tfidf.fit(self.descriptions)
        self.desc_tfidf = self.tfidf.transform(self.descriptions)

        print(f"✓ SemanticMatcher ready — {len(self.classes)} classes: {self.classes}\n")

    # ── Main prediction ───────────────────────────────────────────────────────

    def predict(self, query: str) -> dict:
        """
        Predict the best matching class for a query.

        Returns
        -------
        dict with keys:
            predicted_class : str   — top class label
            confidence      : float — hybrid score of the top class (0–1)
            all_scores      : dict  — hybrid scores for every class
            breakdown       : dict  — per-stage scores for transparency
        """
        query = query.strip()

        # ── Stage 1: Lexical (TF-IDF cosine) ─────────────────────────────────
        query_tfidf   = self.tfidf.transform([query])
        lexical_scores = cosine_similarity(query_tfidf, self.desc_tfidf)[0]

        # ── Stage 2: Semantic (bi-encoder cosine) ─────────────────────────────
        query_emb      = self.bi_encoder.encode([query], convert_to_numpy=True)
        semantic_scores = cosine_similarity(query_emb, self.desc_embeddings)[0]

        # ── Stage 3: Contextual (cross-encoder on top-k candidates) ──────────
        top_k_idx    = np.argsort(semantic_scores)[::-1][: self.top_k_rerank]
        pairs        = [(query, self.descriptions[i]) for i in top_k_idx]
        raw_cx_scores = self.cross_encoder.predict(pairs)

        # Sigmoid-normalise cross-encoder logits → [0, 1]
        contextual_scores = np.zeros(len(self.classes))
        for idx, raw in zip(top_k_idx, raw_cx_scores):
            contextual_scores[idx] = 1.0 / (1.0 + np.exp(-float(raw)))

        # ── Hybrid blend ──────────────────────────────────────────────────────
        w_lex, w_sem, w_ctx = self.weights
        final_scores = (
            w_lex * lexical_scores
            + w_sem * semantic_scores
            + w_ctx * contextual_scores
        )

        best_idx = int(np.argmax(final_scores))

        # ── Build result ──────────────────────────────────────────────────────
        sorted_classes = sorted(
            zip(self.classes, final_scores),
            key=lambda x: -x[1],
        )

        return {
            "predicted_class": self.classes[best_idx],
            "confidence":       round(float(final_scores[best_idx]), 4),
            "ranking":          [(c, round(float(s), 4)) for c, s in sorted_classes],
            "breakdown": {
                "lexical":     {c: round(float(s), 4) for c, s in zip(self.classes, lexical_scores)},
                "semantic":    {c: round(float(s), 4) for c, s in zip(self.classes, semantic_scores)},
                "contextual":  {c: round(float(s), 4) for c, s in zip(self.classes, contextual_scores)},
            },
        }

    def predict_batch(self, queries: list[str]) -> list[dict]:
        """Run predict() over a list of queries."""
        return [self.predict(q) for q in queries]


# ─────────────────────────────────────────────────────────────────────────────
# Pretty-print helper
# ─────────────────────────────────────────────────────────────────────────────

def print_result(query: str, result: dict) -> None:
    bar_w = 30
    print(f"\n{'─'*60}")
    print(f"  Query   : \"{query}\"")
    print(f"  → Class : {result['predicted_class']}  (score: {result['confidence']})")
    print(f"\n  Full ranking:")
    for cls, score in result["ranking"]:
        filled = int(score * bar_w)
        bar    = "█" * filled + "░" * (bar_w - filled)
        marker = " ◀" if cls == result["predicted_class"] else ""
        print(f"    {cls:<20} {bar} {score:.4f}{marker}")

    print(f"\n  Score breakdown (top class):")
    tc = result["predicted_class"]
    print(f"    Lexical    : {result['breakdown']['lexical'][tc]:.4f}")
    print(f"    Semantic   : {result['breakdown']['semantic'][tc]:.4f}")
    print(f"    Contextual : {result['breakdown']['contextual'][tc]:.4f}")
    print(f"{'─'*60}")


# ─────────────────────────────────────────────────────────────────────────────
# Example: Customer Support Ticket Routing
# ─────────────────────────────────────────────────────────────────────────────

SUPPORT_CLASSES = {
    "billing": (
        "Questions about invoices, charges, payment methods, refunds, "
        "subscription costs, pricing plans, discounts, and billing cycles."
    ),
    "technical_issue": (
        "Problems with software bugs, crashes, error messages, login failures, "
        "performance issues, and unexpected application behavior."
    ),
    "account_management": (
        "Requests to update personal information, change passwords, manage "
        "user profiles, delete accounts, or transfer account ownership."
    ),
    "product_feature": (
        "Questions about how to use product features, feature availability, "
        "how-to guides, tutorials, and product capabilities."
    ),
    "shipping_delivery": (
        "Inquiries about order status, tracking numbers, delivery timelines, "
        "lost packages, shipping costs, and delivery address changes."
    ),
    "returns_refunds": (
        "Requests to return an item, initiate a refund, exchange a product, "
        "report a damaged or incorrect item, and return policy questions."
    ),
    "general_inquiry": (
        "General questions about the company, partnership opportunities, "
        "press inquiries, careers, and unclassified customer messages."
    ),
}

TEST_QUERIES = [
    "I was charged twice for my last invoice, please fix this",
    "The app keeps crashing when I try to export my report",
    "How do I reset my password?",
    "Can you explain what the premium plan includes?",
    "My package was supposed to arrive yesterday and still hasn't",
    "I want to send back the shoes I bought, they don't fit",
    "I'd like to explore a partnership with your company",
    "I got an error 500 when logging in from my phone",
    "What payment methods do you accept?",
    "Is there a way to bulk-import contacts into the CRM?",
]


if __name__ == "__main__":
    # ── Initialise ────────────────────────────────────────────────────────────
    matcher = SemanticMatcher(
        class_descriptions=SUPPORT_CLASSES,
        bi_encoder_model="all-MiniLM-L6-v2",          # swap to all-mpnet-base-v2 for better accuracy
        cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        weights=(0.15, 0.50, 0.35),                    # lexical / semantic / contextual
        top_k_rerank=3,
    )

    # ── Run test queries ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("   SEMANTIC MATCHER — TEST RESULTS")
    print("="*60)

    for query in TEST_QUERIES:
        result = matcher.predict(query)
        print_result(query, result)

    # ── Interactive mode ──────────────────────────────────────────────────────
    print("\n\nEntering interactive mode. Type 'quit' to exit.\n")
    while True:
        user_input = input("Enter query: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        result = matcher.predict(user_input)
        print_result(user_input, result)