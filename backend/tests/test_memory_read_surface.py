from app.mind import memory, memory_read


def test_memory_facade_reexports_read_surface_owners() -> None:
    names = (
        "MemorySearchBody",
        "MemoryFactsQueryBody",
        "MemoryGraphExploreBody",
        "handle_memory_search",
        "handle_memory_facts",
        "handle_memory_graph",
        "handle_memory_read",
    )

    for name in names:
        assert getattr(memory, name) is getattr(memory_read, name)
