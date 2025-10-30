"""
Compliance Framework Module

This module provides comprehensive compliance management including:
- SOC2, GDPR, HIPAA, and other compliance frameworks
- Automated compliance controls and monitoring
- Evidence collection and audit trail
- Risk assessment and remediation
- Compliance reporting and certification support
- Policy management and enforcement
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    CCPA = "ccpa"
    PIPEDA = "pipeda"


class ControlCategory(Enum):
    """Control categories"""
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    SYSTEM_MONITORING = "system_monitoring"
    INCIDENT_RESPONSE = "incident_response"
    CHANGE_MANAGEMENT = "change_management"
    VENDOR_MANAGEMENT = "vendor_management"
    BUSINESS_CONTINUITY = "business_continuity"
    RISK_MANAGEMENT = "risk_management"
    PHYSICAL_SECURITY = "physical_security"
    NETWORK_SECURITY = "network_security"


class ControlStatus(Enum):
    """Control implementation status"""
    NOT_IMPLEMENTED = "not_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    NEEDS_REMEDIATION = "needs_remediation"
    UNDER_REVIEW = "under_review"


class RiskLevel(Enum):
    """Risk assessment levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class EvidenceType(Enum):
    """Types of compliance evidence"""
    CONFIGURATION = "configuration"
    LOG_DATA = "log_data"
    SCREENSHOT = "screenshot"
    DOCUMENT = "document"
    AUDIT_REPORT = "audit_report"
    POLICY = "policy"
    PROCEDURE = "procedure"
    TRAINING_RECORD = "training_record"
    CERTIFICATION = "certification"


@dataclass
class ComplianceControl:
    """Individual compliance control"""
    id: str
    framework: ComplianceFramework
    control_id: str  # Framework-specific control ID (e.g., CC6.1 for SOC2)
    title: str
    description: str
    category: ControlCategory
    requirements: List[str]
    implementation_guidance: str
    testing_procedures: List[str]
    evidence_requirements: List[EvidenceType]
    responsible_party: str
    review_frequency: str  # e.g., "monthly", "quarterly", "annually"
    status: ControlStatus = ControlStatus.NOT_IMPLEMENTED
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    remediation_notes: str = ""
    
    def __post_init__(self):
        if isinstance(self.framework, str):
            self.framework = ComplianceFramework(self.framework)
        if isinstance(self.category, str):
            self.category = ControlCategory(self.category)
        if isinstance(self.status, str):
            self.status = ControlStatus(self.status)


@dataclass
class ComplianceEvidence:
    """Evidence supporting compliance controls"""
    id: str
    control_id: str
    evidence_type: EvidenceType
    title: str
    description: str
    collected_date: datetime
    collector: str
    file_path: Optional[str]
    metadata: Dict[str, Any]
    hash_value: str
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.evidence_type, str):
            self.evidence_type = EvidenceType(self.evidence_type)


@dataclass
class RiskAssessment:
    """Risk assessment for compliance"""
    id: str
    title: str
    description: str
    category: str
    risk_level: RiskLevel
    likelihood: int  # 1-5 scale
    impact: int  # 1-5 scale
    risk_score: float  # calculated from likelihood * impact
    mitigation_controls: List[str]
    residual_risk: RiskLevel
    owner: str
    assessment_date: datetime
    review_date: datetime
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.risk_level, str):
            self.risk_level = RiskLevel(self.risk_level)
        if isinstance(self.residual_risk, str):
            self.residual_risk = RiskLevel(self.residual_risk)
        
        # Calculate risk score
        self.risk_score = float(self.likelihood * self.impact)


@dataclass
class CompliancePolicy:
    """Compliance policy definition"""
    id: str
    title: str
    description: str
    framework: ComplianceFramework
    policy_text: str
    version: str
    effective_date: datetime
    review_date: datetime
    approved_by: str
    applicable_controls: List[str]
    related_procedures: List[str]
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.framework, str):
            self.framework = ComplianceFramework(self.framework)


@dataclass
class ComplianceReport:
    """Compliance assessment report"""
    id: str
    framework: ComplianceFramework
    tenant_id: Optional[str]
    report_period_start: datetime
    report_period_end: datetime
    generated_date: datetime
    total_controls: int
    implemented_controls: int
    partially_implemented_controls: int
    not_implemented_controls: int
    compliance_percentage: float
    critical_findings: List[str]
    recommendations: List[str]
    evidence_count: int
    next_assessment_date: datetime
    
    def __post_init__(self):
        if isinstance(self.framework, str):
            self.framework = ComplianceFramework(self.framework)


class ComplianceManager:
    """Comprehensive compliance management system"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        
        # Initialize compliance frameworks
        self.frameworks = {
            ComplianceFramework.SOC2: self._initialize_soc2_controls(),
            ComplianceFramework.GDPR: self._initialize_gdpr_controls(),
            ComplianceFramework.HIPAA: self._initialize_hipaa_controls(),
            ComplianceFramework.ISO_27001: self._initialize_iso27001_controls()
        }
        
        # Storage for compliance data
        self.controls: Dict[str, ComplianceControl] = {}
        self.evidence: Dict[str, ComplianceEvidence] = {}
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        self.policies: Dict[str, CompliancePolicy] = {}
        
        # Initialize controls from frameworks
        self._load_framework_controls()
    
    def _initialize_soc2_controls(self) -> List[ComplianceControl]:
        """Initialize SOC2 Type II controls"""
        return [
            ComplianceControl(
                id="soc2_cc6_1",
                framework=ComplianceFramework.SOC2,
                control_id="CC6.1",
                title="Logical and Physical Access Controls",
                description="The entity implements logical and physical access security software, infrastructure, and processes to meet criteria for access control.",
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Implement multi-factor authentication",
                    "Enforce principle of least privilege",
                    "Regular access reviews and recertification",
                    "Physical access controls for data centers"
                ],
                implementation_guidance="Implement role-based access control with MFA for all privileged accounts",
                testing_procedures=[
                    "Review user access matrix",
                    "Test MFA implementation",
                    "Verify access revocation process"
                ],
                evidence_requirements=[
                    EvidenceType.CONFIGURATION,
                    EvidenceType.LOG_DATA,
                    EvidenceType.POLICY
                ],
                responsible_party="Security Team",
                review_frequency="quarterly"
            ),
            ComplianceControl(
                id="soc2_cc6_2",
                framework=ComplianceFramework.SOC2,
                control_id="CC6.2",
                title="System Boundaries and Data Flow",
                description="System boundaries and data flow are documented and reviewed.",
                category=ControlCategory.SYSTEM_MONITORING,
                requirements=[
                    "Document system boundaries",
                    "Map data flows between systems",
                    "Identify trust boundaries",
                    "Regular review and update of documentation"
                ],
                implementation_guidance="Maintain current system architecture diagrams with data flow mapping",
                testing_procedures=[
                    "Review system documentation",
                    "Verify data flow accuracy",
                    "Test boundary controls"
                ],
                evidence_requirements=[
                    EvidenceType.DOCUMENT,
                    EvidenceType.CONFIGURATION
                ],
                responsible_party="Architecture Team",
                review_frequency="annually"
            ),
            ComplianceControl(
                id="soc2_cc6_3",
                framework=ComplianceFramework.SOC2,
                control_id="CC6.3",
                title="Audit Logs",
                description="The entity creates and maintains complete, accurate, and timely system audit logs.",
                category=ControlCategory.SYSTEM_MONITORING,
                requirements=[
                    "Log all privileged activities",
                    "Centralized log management",
                    "Log integrity protection",
                    "Regular log review and analysis"
                ],
                implementation_guidance="Implement comprehensive logging with SIEM for analysis",
                testing_procedures=[
                    "Review log configuration",
                    "Test log integrity",
                    "Verify completeness of logged events"
                ],
                evidence_requirements=[
                    EvidenceType.CONFIGURATION,
                    EvidenceType.LOG_DATA,
                    EvidenceType.AUDIT_REPORT
                ],
                responsible_party="Security Operations",
                review_frequency="monthly"
            )
        ]
    
    def _initialize_gdpr_controls(self) -> List[ComplianceControl]:
        """Initialize GDPR controls"""
        return [
            ComplianceControl(
                id="gdpr_art5",
                framework=ComplianceFramework.GDPR,
                control_id="Article 5",
                title="Principles of Processing Personal Data",
                description="Personal data shall be processed lawfully, fairly, and transparently.",
                category=ControlCategory.DATA_PROTECTION,
                requirements=[
                    "Lawful basis for processing",
                    "Purpose limitation",
                    "Data minimization",
                    "Accuracy requirements",
                    "Storage limitation",
                    "Integrity and confidentiality"
                ],
                implementation_guidance="Implement data classification and processing controls",
                testing_procedures=[
                    "Review data processing activities",
                    "Verify lawful basis documentation",
                    "Test data retention controls"
                ],
                evidence_requirements=[
                    EvidenceType.POLICY,
                    EvidenceType.DOCUMENT,
                    EvidenceType.PROCEDURE
                ],
                responsible_party="Data Protection Officer",
                review_frequency="quarterly"
            ),
            ComplianceControl(
                id="gdpr_art32",
                framework=ComplianceFramework.GDPR,
                control_id="Article 32",
                title="Security of Processing",
                description="Implement appropriate technical and organizational measures to ensure security.",
                category=ControlCategory.DATA_PROTECTION,
                requirements=[
                    "Encryption of personal data",
                    "Ability to ensure confidentiality",
                    "Ability to restore availability",
                    "Regular testing and evaluation"
                ],
                implementation_guidance="Implement encryption at rest and in transit for personal data",
                testing_procedures=[
                    "Verify encryption implementation",
                    "Test backup and recovery",
                    "Review security measures"
                ],
                evidence_requirements=[
                    EvidenceType.CONFIGURATION,
                    EvidenceType.AUDIT_REPORT,
                    EvidenceType.CERTIFICATION
                ],
                responsible_party="Security Team",
                review_frequency="quarterly"
            )
        ]
    
    def _initialize_hipaa_controls(self) -> List[ComplianceControl]:
        """Initialize HIPAA controls"""
        return [
            ComplianceControl(
                id="hipaa_164_308",
                framework=ComplianceFramework.HIPAA,
                control_id="164.308",
                title="Administrative Safeguards",
                description="Implement administrative safeguards for PHI protection.",
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Security Officer designation",
                    "Information access management",
                    "Workforce training",
                    "Contingency plan",
                    "Security incident procedures"
                ],
                implementation_guidance="Establish comprehensive administrative controls for PHI",
                testing_procedures=[
                    "Review administrative procedures",
                    "Verify training records",
                    "Test incident response"
                ],
                evidence_requirements=[
                    EvidenceType.POLICY,
                    EvidenceType.TRAINING_RECORD,
                    EvidenceType.PROCEDURE
                ],
                responsible_party="Compliance Officer",
                review_frequency="annually"
            ),
            ComplianceControl(
                id="hipaa_164_312",
                framework=ComplianceFramework.HIPAA,
                control_id="164.312",
                title="Technical Safeguards",
                description="Implement technical safeguards for PHI protection.",
                category=ControlCategory.DATA_PROTECTION,
                requirements=[
                    "Access control",
                    "Audit controls",
                    "Integrity controls",
                    "Person or entity authentication",
                    "Transmission security"
                ],
                implementation_guidance="Implement technical controls for PHI access and transmission",
                testing_procedures=[
                    "Test access controls",
                    "Review audit logs",
                    "Verify encryption"
                ],
                evidence_requirements=[
                    EvidenceType.CONFIGURATION,
                    EvidenceType.LOG_DATA,
                    EvidenceType.AUDIT_REPORT
                ],
                responsible_party="IT Security",
                review_frequency="quarterly"
            )
        ]
    
    def _initialize_iso27001_controls(self) -> List[ComplianceControl]:
        """Initialize ISO 27001 controls"""
        return [
            ComplianceControl(
                id="iso27001_a5_1_1",
                framework=ComplianceFramework.ISO_27001,
                control_id="A.5.1.1",
                title="Information Security Policy",
                description="A set of policies for information security shall be defined.",
                category=ControlCategory.RISK_MANAGEMENT,
                requirements=[
                    "Information security policy document",
                    "Management approval",
                    "Regular review and updates",
                    "Communication to stakeholders"
                ],
                implementation_guidance="Develop comprehensive information security policy",
                testing_procedures=[
                    "Review policy documentation",
                    "Verify management approval",
                    "Test communication effectiveness"
                ],
                evidence_requirements=[
                    EvidenceType.POLICY,
                    EvidenceType.DOCUMENT
                ],
                responsible_party="CISO",
                review_frequency="annually"
            )
        ]
    
    def _load_framework_controls(self):
        """Load controls from all frameworks"""
        for framework, controls in self.frameworks.items():
            for control in controls:
                self.controls[control.id] = control
    
    def assess_control_compliance(self, control_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Assess compliance for a specific control"""
        try:
            if control_id not in self.controls:
                raise ValueError(f"Control not found: {control_id}")
            
            control = self.controls[control_id]
            
            # Collect evidence for the control
            control_evidence = [
                evidence for evidence in self.evidence.values()
                if evidence.control_id == control_id and 
                (tenant_id is None or evidence.tenant_id == tenant_id)
            ]
            
            # Determine compliance status based on evidence
            compliance_status = self._evaluate_control_compliance(control, control_evidence)
            
            assessment_result = {
                "control_id": control_id,
                "framework": control.framework.value,
                "title": control.title,
                "status": compliance_status.value,
                "evidence_count": len(control_evidence),
                "last_assessment": datetime.utcnow().isoformat(),
                "findings": [],
                "recommendations": []
            }
            
            # Add findings and recommendations based on status
            if compliance_status == ControlStatus.NOT_IMPLEMENTED:
                assessment_result["findings"].append("Control not implemented")
                assessment_result["recommendations"].append("Implement required control measures")
            elif compliance_status == ControlStatus.PARTIALLY_IMPLEMENTED:
                assessment_result["findings"].append("Control partially implemented")
                assessment_result["recommendations"].append("Complete control implementation")
            elif compliance_status == ControlStatus.NEEDS_REMEDIATION:
                assessment_result["findings"].append("Control requires remediation")
                assessment_result["recommendations"].append("Address identified deficiencies")
            
            return assessment_result
            
        except Exception as e:
            logger.error(f"Failed to assess control compliance: {e}")
            raise
    
    def _evaluate_control_compliance(self, control: ComplianceControl, 
                                   evidence: List[ComplianceEvidence]) -> ControlStatus:
        """Evaluate control compliance based on evidence"""
        if not evidence:
            return ControlStatus.NOT_IMPLEMENTED
        
        # Check if all required evidence types are present
        required_evidence_types = set(control.evidence_requirements)
        available_evidence_types = set(e.evidence_type for e in evidence)
        
        if required_evidence_types.issubset(available_evidence_types):
            # All required evidence is available
            # Additional logic could check evidence quality, recency, etc.
            return ControlStatus.IMPLEMENTED
        elif available_evidence_types:
            # Some evidence is available but not complete
            return ControlStatus.PARTIALLY_IMPLEMENTED
        else:
            return ControlStatus.NOT_IMPLEMENTED
    
    def generate_compliance_report(self, framework: ComplianceFramework,
                                 tenant_id: Optional[str] = None,
                                 report_period_days: int = 90) -> ComplianceReport:
        """Generate comprehensive compliance report"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=report_period_days)
            
            # Get controls for the framework
            framework_controls = [
                control for control in self.controls.values()
                if control.framework == framework
            ]
            
            # Assess each control
            implemented_count = 0
            partially_implemented_count = 0
            not_implemented_count = 0
            critical_findings = []
            recommendations = []
            
            for control in framework_controls:
                assessment = self.assess_control_compliance(control.id, tenant_id)
                
                if assessment["status"] == ControlStatus.IMPLEMENTED.value:
                    implemented_count += 1
                elif assessment["status"] == ControlStatus.PARTIALLY_IMPLEMENTED.value:
                    partially_implemented_count += 1
                else:
                    not_implemented_count += 1
                
                # Collect critical findings
                if control.category in [ControlCategory.ACCESS_CONTROL, ControlCategory.DATA_PROTECTION]:
                    if assessment["status"] != ControlStatus.IMPLEMENTED.value:
                        critical_findings.extend(assessment["findings"])
                
                recommendations.extend(assessment["recommendations"])
            
            total_controls = len(framework_controls)
            compliance_percentage = (implemented_count / total_controls * 100) if total_controls > 0 else 0
            
            # Count evidence
            evidence_count = len([
                e for e in self.evidence.values()
                if tenant_id is None or e.tenant_id == tenant_id
            ])
            
            report = ComplianceReport(
                id=str(uuid.uuid4()),
                framework=framework,
                tenant_id=tenant_id,
                report_period_start=start_date,
                report_period_end=end_date,
                generated_date=datetime.utcnow(),
                total_controls=total_controls,
                implemented_controls=implemented_count,
                partially_implemented_controls=partially_implemented_count,
                not_implemented_controls=not_implemented_count,
                compliance_percentage=compliance_percentage,
                critical_findings=critical_findings[:10],  # Top 10 critical findings
                recommendations=list(set(recommendations))[:10],  # Top 10 unique recommendations
                evidence_count=evidence_count,
                next_assessment_date=end_date + timedelta(days=90)
            )
            
            logger.info(f"Generated compliance report for {framework.value}: {compliance_percentage:.1f}% compliant")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise
    
    def collect_evidence(self, control_id: str, evidence_type: EvidenceType,
                        title: str, description: str, file_path: Optional[str] = None,
                        metadata: Dict[str, Any] = None, tenant_id: Optional[str] = None) -> str:
        """Collect and store compliance evidence"""
        try:
            evidence_id = str(uuid.uuid4())
            
            # Calculate hash for integrity
            hash_input = f"{control_id}{title}{description}{datetime.utcnow().isoformat()}"
            hash_value = hashlib.sha256(hash_input.encode()).hexdigest()
            
            evidence = ComplianceEvidence(
                id=evidence_id,
                control_id=control_id,
                evidence_type=evidence_type,
                title=title,
                description=description,
                collected_date=datetime.utcnow(),
                collector="system",  # Would get from context
                file_path=file_path,
                metadata=metadata or {},
                hash_value=hash_value,
                tenant_id=tenant_id
            )
            
            self.evidence[evidence_id] = evidence
            
            logger.info(f"Collected evidence for control {control_id}: {evidence_id}")
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to collect evidence: {e}")
            raise
    
    def perform_risk_assessment(self, title: str, description: str, category: str,
                              likelihood: int, impact: int, mitigation_controls: List[str],
                              owner: str, tenant_id: Optional[str] = None) -> str:
        """Perform risk assessment"""
        try:
            risk_id = str(uuid.uuid4())
            
            # Calculate risk level based on score
            risk_score = likelihood * impact
            if risk_score >= 20:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 15:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 10:
                risk_level = RiskLevel.MEDIUM
            elif risk_score >= 5:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.INFORMATIONAL
            
            # Assume mitigation reduces risk by one level
            residual_risk_score = max(1, risk_score - 5)  # Reduce by 5 points with mitigation
            if residual_risk_score >= 20:
                residual_risk = RiskLevel.CRITICAL
            elif residual_risk_score >= 15:
                residual_risk = RiskLevel.HIGH
            elif residual_risk_score >= 10:
                residual_risk = RiskLevel.MEDIUM
            elif residual_risk_score >= 5:
                residual_risk = RiskLevel.LOW
            else:
                residual_risk = RiskLevel.INFORMATIONAL
            
            risk_assessment = RiskAssessment(
                id=risk_id,
                title=title,
                description=description,
                category=category,
                risk_level=risk_level,
                likelihood=likelihood,
                impact=impact,
                risk_score=float(risk_score),
                mitigation_controls=mitigation_controls,
                residual_risk=residual_risk,
                owner=owner,
                assessment_date=datetime.utcnow(),
                review_date=datetime.utcnow() + timedelta(days=90),
                tenant_id=tenant_id
            )
            
            self.risk_assessments[risk_id] = risk_assessment
            
            logger.info(f"Performed risk assessment: {risk_id} - {risk_level.value}")
            return risk_id
            
        except Exception as e:
            logger.error(f"Failed to perform risk assessment: {e}")
            raise
    
    def create_compliance_policy(self, title: str, description: str, framework: ComplianceFramework,
                               policy_text: str, version: str, approved_by: str,
                               applicable_controls: List[str], tenant_id: Optional[str] = None) -> str:
        """Create compliance policy"""
        try:
            policy_id = str(uuid.uuid4())
            
            policy = CompliancePolicy(
                id=policy_id,
                title=title,
                description=description,
                framework=framework,
                policy_text=policy_text,
                version=version,
                effective_date=datetime.utcnow(),
                review_date=datetime.utcnow() + timedelta(days=365),  # Annual review
                approved_by=approved_by,
                applicable_controls=applicable_controls,
                related_procedures=[],
                tenant_id=tenant_id
            )
            
            self.policies[policy_id] = policy
            
            logger.info(f"Created compliance policy: {policy_id} for {framework.value}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Failed to create compliance policy: {e}")
            raise
    
    def get_compliance_dashboard(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance dashboard data"""
        try:
            dashboard_data = {
                "overall_compliance": {},
                "framework_status": {},
                "recent_assessments": [],
                "critical_risks": [],
                "upcoming_reviews": [],
                "evidence_summary": {
                    "total_evidence": 0,
                    "recent_evidence": 0
                }
            }
            
            # Calculate overall compliance by framework
            for framework in ComplianceFramework:
                try:
                    report = self.generate_compliance_report(framework, tenant_id, 30)
                    dashboard_data["framework_status"][framework.value] = {
                        "compliance_percentage": report.compliance_percentage,
                        "total_controls": report.total_controls,
                        "implemented_controls": report.implemented_controls,
                        "critical_findings_count": len(report.critical_findings)
                    }
                except Exception:
                    continue
            
            # Get recent risk assessments
            recent_risks = sorted(
                [r for r in self.risk_assessments.values() 
                 if tenant_id is None or r.tenant_id == tenant_id],
                key=lambda x: x.assessment_date,
                reverse=True
            )[:5]
            
            dashboard_data["recent_assessments"] = [
                {
                    "id": risk.id,
                    "title": risk.title,
                    "risk_level": risk.risk_level.value,
                    "assessment_date": risk.assessment_date.isoformat()
                }
                for risk in recent_risks
            ]
            
            # Get critical risks
            critical_risks = [
                r for r in self.risk_assessments.values()
                if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH] and
                (tenant_id is None or r.tenant_id == tenant_id)
            ]
            
            dashboard_data["critical_risks"] = [
                {
                    "id": risk.id,
                    "title": risk.title,
                    "risk_level": risk.risk_level.value,
                    "risk_score": risk.risk_score
                }
                for risk in critical_risks[:10]
            ]
            
            # Evidence summary
            tenant_evidence = [
                e for e in self.evidence.values()
                if tenant_id is None or e.tenant_id == tenant_id
            ]
            
            recent_evidence = [
                e for e in tenant_evidence
                if e.collected_date >= datetime.utcnow() - timedelta(days=30)
            ]
            
            dashboard_data["evidence_summary"] = {
                "total_evidence": len(tenant_evidence),
                "recent_evidence": len(recent_evidence)
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to generate compliance dashboard: {e}")
            raise
    
    def get_control_by_id(self, control_id: str) -> Optional[ComplianceControl]:
        """Get control by ID"""
        return self.controls.get(control_id)
    
    def list_controls_by_framework(self, framework: ComplianceFramework) -> List[ComplianceControl]:
        """List controls for a specific framework"""
        return [
            control for control in self.controls.values()
            if control.framework == framework
        ]
    
    def update_control_status(self, control_id: str, status: ControlStatus, 
                            remediation_notes: str = ""):
        """Update control implementation status"""
        if control_id in self.controls:
            control = self.controls[control_id]
            control.status = status
            control.last_review_date = datetime.utcnow()
            control.remediation_notes = remediation_notes
            
            # Set next review date
            if control.review_frequency == "monthly":
                control.next_review_date = datetime.utcnow() + timedelta(days=30)
            elif control.review_frequency == "quarterly":
                control.next_review_date = datetime.utcnow() + timedelta(days=90)
            else:  # annually
                control.next_review_date = datetime.utcnow() + timedelta(days=365)
            
            logger.info(f"Updated control {control_id} status to {status.value}")


class TenantComplianceManager:
    """Tenant-specific compliance management"""
    
    def __init__(self, compliance_manager: ComplianceManager, tenant_id: str):
        self.compliance_manager = compliance_manager
        self.tenant_id = tenant_id
    
    def setup_tenant_compliance(self, required_frameworks: List[ComplianceFramework]):
        """Setup compliance monitoring for tenant"""
        try:
            for framework in required_frameworks:
                # Generate initial compliance report
                report = self.compliance_manager.generate_compliance_report(
                    framework, self.tenant_id
                )
                
                # Create baseline policies
                self._create_baseline_policies(framework)
                
                # Perform initial risk assessment
                self._perform_initial_risk_assessment()
            
            logger.info(f"Setup compliance for tenant {self.tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup tenant compliance: {e}")
            raise
    
    def _create_baseline_policies(self, framework: ComplianceFramework):
        """Create baseline policies for framework"""
        if framework == ComplianceFramework.GDPR:
            self.compliance_manager.create_compliance_policy(
                title="GDPR Data Protection Policy",
                description="Policy for GDPR compliance and data protection",
                framework=framework,
                policy_text="This policy outlines requirements for GDPR compliance...",
                version="1.0",
                approved_by=f"Tenant {self.tenant_id} Admin",
                applicable_controls=["gdpr_art5", "gdpr_art32"],
                tenant_id=self.tenant_id
            )
        elif framework == ComplianceFramework.SOC2:
            self.compliance_manager.create_compliance_policy(
                title="SOC2 Security Policy",
                description="Policy for SOC2 security controls",
                framework=framework,
                policy_text="This policy defines security controls for SOC2 compliance...",
                version="1.0",
                approved_by=f"Tenant {self.tenant_id} Admin",
                applicable_controls=["soc2_cc6_1", "soc2_cc6_2", "soc2_cc6_3"],
                tenant_id=self.tenant_id
            )
    
    def _perform_initial_risk_assessment(self):
        """Perform initial risk assessment"""
        # Data breach risk
        self.compliance_manager.perform_risk_assessment(
            title="Data Breach Risk",
            description="Risk of unauthorized access to sensitive data",
            category="Data Security",
            likelihood=3,
            impact=5,
            mitigation_controls=["encryption", "access_control", "monitoring"],
            owner=f"Tenant {self.tenant_id} Security Team",
            tenant_id=self.tenant_id
        )
        
        # System availability risk
        self.compliance_manager.perform_risk_assessment(
            title="System Availability Risk",
            description="Risk of system downtime affecting business operations",
            category="Business Continuity",
            likelihood=2,
            impact=4,
            mitigation_controls=["backup_systems", "monitoring", "incident_response"],
            owner=f"Tenant {self.tenant_id} Operations Team",
            tenant_id=self.tenant_id
        )
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status for tenant"""
        return self.compliance_manager.get_compliance_dashboard(self.tenant_id)
    
    def collect_audit_evidence(self, control_id: str, evidence_type: EvidenceType,
                              title: str, description: str, file_path: Optional[str] = None):
        """Collect evidence for tenant"""
        return self.compliance_manager.collect_evidence(
            control_id, evidence_type, title, description, file_path, tenant_id=self.tenant_id
        )


# Example usage
if __name__ == "__main__":
    # Initialize compliance manager
    compliance_manager = ComplianceManager("ai-data-analyst-project")
    
    # Initialize tenant compliance
    tenant_compliance = TenantComplianceManager(compliance_manager, "tenant-123")
    
    # Setup compliance for tenant
    tenant_compliance.setup_tenant_compliance([
        ComplianceFramework.SOC2,
        ComplianceFramework.GDPR
    ])
    
    # Collect some evidence
    tenant_compliance.collect_audit_evidence(
        control_id="soc2_cc6_1",
        evidence_type=EvidenceType.CONFIGURATION,
        title="MFA Configuration",
        description="Multi-factor authentication configuration for all users"
    )
    
    # Generate compliance reports
    soc2_report = compliance_manager.generate_compliance_report(
        ComplianceFramework.SOC2, "tenant-123"
    )
    
    gdpr_report = compliance_manager.generate_compliance_report(
        ComplianceFramework.GDPR, "tenant-123"
    )
    
    # Get compliance dashboard
    dashboard = tenant_compliance.get_compliance_status()
    
    print(f"SOC2 Compliance: {soc2_report.compliance_percentage:.1f}%")
    print(f"GDPR Compliance: {gdpr_report.compliance_percentage:.1f}%")
    print(f"Total Evidence Collected: {dashboard['evidence_summary']['total_evidence']}")
    print(f"Critical Risks: {len(dashboard['critical_risks'])}")