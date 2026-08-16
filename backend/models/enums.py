from enum import Enum
class SourceLane(str, Enum):
    MASTER_BRIEF_GOVERNANCE = "master_brief_governance"
    TERMS_ASSENT_ARBITRATION = "terms_assent_arbitration"
    ACCOUNTING_AUDIT_DERIVATIVE = "accounting_audit_derivative"
    TECHNOLOGY_CONTROL_SHELL = "technology_control_shell"
    BEHAVIORAL_MANIPULATION = "behavioral_manipulation"
    UNKNOWN = "unknown"
class SourcePriority(str, Enum):
    PRIMARY = "primary"; SECONDARY = "secondary"; SUPPORT = "support"; ANALOG = "analog"
class DraftingMode(str, Enum):
    V54_LEAD = "v54_lead"; V52_RETAINED = "v52_retained"; HYBRID = "hybrid"; PENDING = "pending"
class AudienceMode(str, Enum):
    OUTSIDE_COUNSEL = "outside_counsel"; JUDGE = "judge"; JURY_EXPLANATORY = "jury_explanatory"
class AgentName(str, Enum):
    WOLF = "wolf"; TIGER = "tiger"; MASTER_NEXUS = "master_nexus"
class AnchorType(str, Enum):
    DIRECT_PROOF = "direct_proof"; ANALOG_SUPPORT = "analog_support"
    AUDIENCE_EXPLANATION = "audience_explanation"; CONTRACT_CLAUSE = "contract_clause"
    ACCOUNTING_ENTRY = "accounting_entry"; TECHNOLOGY_FACT = "technology_fact"
class BridgeDomain(str, Enum):
    CONTRACT_ARBITRATION = "contract_arbitration"; CONSUMER_PROTECTION = "consumer_protection"
    DERIVATIVES = "derivatives"; ACCOUNTING_AUDIT = "accounting_audit"
    TECHNOLOGY_STACK = "technology_stack"; GNUG_VIE = "gnug_vie"
    AML = "aml"; ESG_PLATFORM = "esg_platform"; RESPONSIBLE_GAMING = "responsible_gaming"
class FlywheelCategory(str, Enum):
    DDF = "ddf"; CDSF = "cdsf"; DDSF = "ddsf"
