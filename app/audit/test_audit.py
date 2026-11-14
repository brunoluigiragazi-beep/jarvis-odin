from app.audit.audit_manager import AuditManager

audit = AuditManager()

result = audit.log_event(
    event_type="system_test",
    actor="ODIN",
    details={
        "message": "Teste inicial do módulo de auditoria",
        "status": "success"
    }
)

print("Evento registrado com sucesso!")
print(result)