"""
Security and Data Sanitization for MetaStackerBandit
Features: ID hashing, PII detection, data masking, audit logging
"""

import hashlib
import re
import json
import os
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import secrets
import base64
from datetime import datetime,timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")


class SensitivityLevel(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataType(Enum):
    WALLET_ADDRESS = "wallet_address"
    EMAIL = "email"
    PHONE = "phone"
    API_KEY = "api_key"
    SECRET = "secret"
    PASSWORD = "password"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    USER_ID = "user_id"
    SESSION_ID = "session_id"


@dataclass
class SanitizationRule:
    pattern: str
    data_type: DataType
    sensitivity: SensitivityLevel
    replacement: str = "[REDACTED]"
    hash_salt: Optional[str] = None
    preserve_length: bool = True
    preserve_format: bool = True


class DataSanitizer:
    """Production data sanitizer with ID hashing and PII detection"""

    def __init__(self, salt: Optional[str] = None):
        self.salt = salt or self._generate_salt()
        self.rules = self._setup_default_rules()
        self.audit_log: List[Dict[str, Any]] = []
        self.hash_cache: Dict[str, str] = {}

    def _generate_salt(self) -> str:
        """Generate cryptographically secure salt"""
        return secrets.token_hex(32)

    def _setup_default_rules(self) -> List[SanitizationRule]:
        """Setup default sanitization rules"""
        return [
            # Wallet addresses (Ethereum, Bitcoin, etc.)
            SanitizationRule(
                pattern=r"0x[a-fA-F0-9]{40}",
                data_type=DataType.WALLET_ADDRESS,
                sensitivity=SensitivityLevel.CONFIDENTIAL,
                replacement="[WALLET_ADDRESS]",
                hash_salt=self.salt,
            ),
            SanitizationRule(
                pattern=r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}",
                data_type=DataType.WALLET_ADDRESS,
                sensitivity=SensitivityLevel.CONFIDENTIAL,
                replacement="[BITCOIN_ADDRESS]",
                hash_salt=self.salt,
            ),
            # Email addresses
            SanitizationRule(
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                data_type=DataType.EMAIL,
                sensitivity=SensitivityLevel.CONFIDENTIAL,
                replacement="[EMAIL]",
                hash_salt=self.salt,
            ),
            # Phone numbers
            SanitizationRule(
                pattern=r"(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",
                data_type=DataType.PHONE,
                sensitivity=SensitivityLevel.CONFIDENTIAL,
                replacement="[PHONE]",
                hash_salt=self.salt,
            ),
            # API Keys (common patterns)
            SanitizationRule(
                pattern=r"[A-Za-z0-9]{20,}",
                data_type=DataType.API_KEY,
                sensitivity=SensitivityLevel.RESTRICTED,
                replacement="[API_KEY]",
                hash_salt=self.salt,
            ),
            # Secrets and passwords
            SanitizationRule(
                pattern=r'(?i)(password|passwd|pwd|secret|key|token)\s*[:=]\s*["\']?[^"\'\s]+["\']?',
                data_type=DataType.SECRET,
                sensitivity=SensitivityLevel.RESTRICTED,
                replacement="[SECRET]",
                hash_salt=self.salt,
            ),
            # Credit card numbers
            SanitizationRule(
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
                data_type=DataType.CREDIT_CARD,
                sensitivity=SensitivityLevel.RESTRICTED,
                replacement="[CREDIT_CARD]",
                hash_salt=self.salt,
            ),
            # SSN
            SanitizationRule(
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                data_type=DataType.SSN,
                sensitivity=SensitivityLevel.RESTRICTED,
                replacement="[SSN]",
                hash_salt=self.salt,
            ),
            # IP addresses
            SanitizationRule(
                pattern=r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
                data_type=DataType.IP_ADDRESS,
                sensitivity=SensitivityLevel.INTERNAL,
                replacement="[IP_ADDRESS]",
                hash_salt=self.salt,
            ),
            # User IDs and session IDs
            SanitizationRule(
                pattern=r'(?i)(user_id|session_id|userid|sessionid)\s*[:=]\s*["\']?[^"\'\s]+["\']?',
                data_type=DataType.USER_ID,
                sensitivity=SensitivityLevel.INTERNAL,
                replacement="[USER_ID]",
                hash_salt=self.salt,
            ),
        ]

    def add_rule(self, rule: SanitizationRule):
        """Add custom sanitization rule"""
        self.rules.append(rule)

    def sanitize_data(self, data: Any, context: Optional[str] = None) -> Any:
        """Sanitize data recursively"""
        if isinstance(data, dict):
            return {
                key: self.sanitize_data(value, f"{context}.{key}" if context else key)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.sanitize_data(item, context) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data, context)
        else:
            return data

    def _sanitize_string(self, text: str, context: Optional[str] = None) -> str:
        """Sanitize string data"""
        if not text:
            return text

        sanitized = text
        detected_types = set()

        for rule in self.rules:
            matches = re.findall(rule.pattern, sanitized)
            if matches:
                detected_types.add(rule.data_type)

                # Replace matches
                if rule.hash_salt:
                    # Hash the original value for audit purposes
                    for match in matches:
                        if isinstance(match, tuple):
                            match = "".join(match)
                        hashed_value = self._hash_value(match, rule.hash_salt)
                        sanitized = re.sub(rule.pattern, rule.replacement, sanitized)
                        self._log_detection(rule, match, hashed_value, context)
                else:
                    sanitized = re.sub(rule.pattern, rule.replacement, sanitized)
                    self._log_detection(
                        rule, matches[0] if matches else "", "", context
                    )

        return sanitized

    def _hash_value(self, value: str, salt: str) -> str:
        """Hash value with salt"""
        # Check cache first
        cache_key = f"{value}:{salt}"
        if cache_key in self.hash_cache:
            return self.hash_cache[cache_key]

        # Create hash
        hash_input = f"{value}:{salt}".encode("utf-8")
        hashed = hashlib.sha256(hash_input).hexdigest()[:16]  # Truncate for readability

        # Cache result
        self.hash_cache[cache_key] = hashed
        return hashed

    def _log_detection(
        self, rule: SanitizationRule, original: str, hashed: str, context: Optional[str]
    ):
        """Log data detection for audit purposes"""
        detection = {
            "timestamp": datetime.now(IST).isoformat(),
            "data_type": rule.data_type.value,
            "sensitivity": rule.sensitivity.value,
            "context": context,
            "original_length": len(original),
            "hashed_value": hashed,
            "rule_pattern": rule.pattern,
        }

        self.audit_log.append(detection)

        # Keep only last 10000 detections
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]

    def hash_wallet_address(self, address: str) -> str:
        """Hash wallet address for consistent identification"""
        if not address:
            return address

        # Normalize address (lowercase for Ethereum)
        normalized = address.lower() if address.startswith("0x") else address

        # Create deterministic hash
        hash_input = f"{normalized}:{self.salt}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def hash_user_id(self, user_id: str) -> str:
        """Hash user ID for consistent identification"""
        if not user_id:
            return user_id

        hash_input = f"user:{user_id}:{self.salt}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def hash_session_id(self, session_id: str) -> str:
        """Hash session ID for consistent identification"""
        if not session_id:
            return session_id

        hash_input = f"session:{session_id}:{self.salt}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def mask_sensitive_fields(
        self, data: Dict[str, Any], sensitive_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Mask sensitive fields in data structure"""
        if sensitive_fields is None:
            sensitive_fields = [
                "password",
                "passwd",
                "pwd",
                "secret",
                "key",
                "token",
                "api_key",
                "api_secret",
                "access_token",
                "refresh_token",
                "private_key",
                "wallet_private_key",
                "mnemonic",
                "ssn",
                "social_security",
                "credit_card",
                "card_number",
            ]

        masked_data = data.copy()

        for key, value in masked_data.items():
            if isinstance(value, dict):
                masked_data[key] = self.mask_sensitive_fields(value, sensitive_fields)
            elif isinstance(value, list):
                masked_data[key] = [
                    (
                        self.mask_sensitive_fields(item, sensitive_fields)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            elif isinstance(value, str) and any(
                field in key.lower() for field in sensitive_fields
            ):
                masked_data[key] = "[MASKED]"

        return masked_data

    def validate_data_classification(
        self, data: Dict[str, Any]
    ) -> Dict[str, SensitivityLevel]:
        """Classify data sensitivity levels"""
        classification = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Check for sensitive patterns
                max_sensitivity = SensitivityLevel.PUBLIC

                for rule in self.rules:
                    if re.search(rule.pattern, value):
                        if rule.sensitivity.value == "restricted":
                            max_sensitivity = SensitivityLevel.RESTRICTED
                        elif (
                            rule.sensitivity.value == "confidential"
                            and max_sensitivity != SensitivityLevel.RESTRICTED
                        ):
                            max_sensitivity = SensitivityLevel.CONFIDENTIAL
                        elif (
                            rule.sensitivity.value == "internal"
                            and max_sensitivity == SensitivityLevel.PUBLIC
                        ):
                            max_sensitivity = SensitivityLevel.INTERNAL

                classification[key] = max_sensitivity
            elif isinstance(value, dict):
                classification[key] = self._get_dict_sensitivity(value)
            else:
                classification[key] = SensitivityLevel.PUBLIC

        return classification

    def _get_dict_sensitivity(self, data: Dict[str, Any]) -> SensitivityLevel:
        """Get sensitivity level for dictionary"""
        max_sensitivity = SensitivityLevel.PUBLIC

        for value in data.values():
            if isinstance(value, str):
                for rule in self.rules:
                    if re.search(rule.pattern, value):
                        if rule.sensitivity.value == "restricted":
                            return SensitivityLevel.RESTRICTED
                        elif (
                            rule.sensitivity.value == "confidential"
                            and max_sensitivity != SensitivityLevel.RESTRICTED
                        ):
                            max_sensitivity = SensitivityLevel.CONFIDENTIAL
                        elif (
                            rule.sensitivity.value == "internal"
                            and max_sensitivity == SensitivityLevel.PUBLIC
                        ):
                            max_sensitivity = SensitivityLevel.INTERNAL
            elif isinstance(value, dict):
                nested_sensitivity = self._get_dict_sensitivity(value)
                if nested_sensitivity.value == "restricted":
                    return SensitivityLevel.RESTRICTED
                elif (
                    nested_sensitivity.value == "confidential"
                    and max_sensitivity != SensitivityLevel.RESTRICTED
                ):
                    max_sensitivity = SensitivityLevel.CONFIDENTIAL
                elif (
                    nested_sensitivity.value == "internal"
                    and max_sensitivity == SensitivityLevel.PUBLIC
                ):
                    max_sensitivity = SensitivityLevel.INTERNAL

        return max_sensitivity

    def get_audit_log(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get audit log for specified hours"""
        cutoff = datetime.now(IST) - timedelta(hours=hours)
        return [
            entry
            for entry in self.audit_log
            if datetime.fromisoformat(entry["timestamp"]) >= cutoff
        ]

    def export_audit_log(self, file_path: str):
        """Export audit log to file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            for entry in self.audit_log:
                f.write(json.dumps(entry) + "\n")

    def get_stats(self) -> Dict[str, Any]:
        """Get sanitizer statistics"""
        recent_detections = self.get_audit_log(24)

        stats = {
            "total_detections": len(self.audit_log),
            "recent_detections": len(recent_detections),
            "rules_count": len(self.rules),
            "hash_cache_size": len(self.hash_cache),
            "detection_types": {},
            "sensitivity_breakdown": {},
        }

        # Count detection types
        for detection in recent_detections:
            data_type = detection["data_type"]
            sensitivity = detection["sensitivity"]

            stats["detection_types"][data_type] = (
                stats["detection_types"].get(data_type, 0) + 1
            )
            stats["sensitivity_breakdown"][sensitivity] = (
                stats["sensitivity_breakdown"].get(sensitivity, 0) + 1
            )

        return stats


# Global sanitizer instance
_sanitizer: Optional[DataSanitizer] = None


def get_sanitizer(salt: Optional[str] = None) -> DataSanitizer:
    """Get global data sanitizer instance"""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = DataSanitizer(salt)
    return _sanitizer


def sanitize_log_record(
    record: Dict[str, Any], context: Optional[str] = None
) -> Dict[str, Any]:
    """Sanitize log record using global sanitizer"""
    sanitizer = get_sanitizer()
    return sanitizer.sanitize_data(record, context)


def hash_identifiers(record: Dict[str, Any]) -> Dict[str, Any]:
    """Hash identifiers in record"""
    sanitizer = get_sanitizer()
    hashed_record = record.copy()

    # Hash common identifier fields
    id_fields = ["user_id", "session_id", "wallet_address", "address", "account_id"]

    for field in id_fields:
        if field in hashed_record and hashed_record[field]:
            if "wallet" in field or "address" in field:
                hashed_record[field] = sanitizer.hash_wallet_address(
                    hashed_record[field]
                )
            elif "user" in field:
                hashed_record[field] = sanitizer.hash_user_id(hashed_record[field])
            elif "session" in field:
                hashed_record[field] = sanitizer.hash_session_id(hashed_record[field])

    return hashed_record
