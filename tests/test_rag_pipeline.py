from rag.rag_pipeline import RAGPipeline


def test_rag_pipeline_initializes():
    pipeline = RAGPipeline()

    assert pipeline.retriever is not None
    assert pipeline.evidence_extractor is not None
    assert pipeline.verifier is not None
    assert pipeline.explainer is not None