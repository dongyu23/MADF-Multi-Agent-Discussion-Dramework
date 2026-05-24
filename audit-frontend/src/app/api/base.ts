const isStandaloneAudit = window.location.port === "81";

export const AUDIT_API_BASE = isStandaloneAudit ? "/api/v1" : "/audit/api/v1";
export const AUDIT_LOGIN_PATH = "/audit/login";
