from langgraph.checkpoint.memory import MemorySaver

_checkpointer = MemorySaver() # Create it once globally

async def get_checkpointer(engine):
    # We ignore the engine argument completely
    return _checkpointer