import uuid

def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

def project_id() -> str: return gen_id("PROJ")
def source_id() -> str: return gen_id("SRC")
def chunk_id() -> str: return gen_id("CHUNK")
def section_id() -> str: return gen_id("SEC")
def section_version_id() -> str: return gen_id("SECV")
def anchor_id() -> str: return gen_id("ANC")
def support_link_id() -> str: return gen_id("SLINK")
def bridge_id() -> str: return gen_id("BRDG")
def bridge_anchor_link_id() -> str: return gen_id("BALINK")
def protocol_id() -> str: return gen_id("PROTO")
def protocol_run_id() -> str: return gen_id("PRUN")
def flywheel_id() -> str: return gen_id("FW")
def merge_decision_id() -> str: return gen_id("MERGE")
def artifact_id() -> str: return gen_id("ART")
