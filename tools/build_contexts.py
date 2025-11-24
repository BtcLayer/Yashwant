from ops.llm_logging import build_llm_context_pack, build_llm_context_bundle

if __name__ == "__main__":
    p1 = build_llm_context_pack()
    print(p1)
    p2 = build_llm_context_bundle()
    print(p2)
