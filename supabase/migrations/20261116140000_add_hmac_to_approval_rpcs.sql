
BEGIN;

-- =====================================================
-- 1. REMOVE AS ASSINATURAS ANTIGAS
-- =====================================================

DROP FUNCTION IF EXISTS public.odin_request_approval_v2(
    uuid, text, integer, text, text, jsonb
);

DROP FUNCTION IF EXISTS public.odin_claim_approval_v2(
    uuid, text, integer, text
);


-- =====================================================
-- 2. SOLICITAÇÃO DE APROVAÇÃO
-- =====================================================

CREATE OR REPLACE FUNCTION public.odin_request_approval_v2(
    p_execution_id uuid,
    p_thread_id text,
    p_step_id integer,
    p_action_type text,
    p_description text,
    p_action_hash text,
    p_parameters jsonb DEFAULT '{}'::jsonb
)
RETURNS SETOF public.odin_approvals
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO ''
AS $function$

DECLARE
    created_approval public.odin_approvals%ROWTYPE;

BEGIN

    IF p_execution_id IS NULL THEN
        RAISE EXCEPTION 'ID da execução inválido.';
    END IF;

    IF p_thread_id IS NULL OR btrim(p_thread_id) = '' THEN
        RAISE EXCEPTION 'Thread ID inválido.';
    END IF;

    IF p_step_id IS NULL OR p_step_id < 1 THEN
        RAISE EXCEPTION 'ID da etapa inválido.';
    END IF;

    IF p_action_type IS NULL OR btrim(p_action_type) = '' THEN
        RAISE EXCEPTION 'Tipo de ação inválido.';
    END IF;

    IF p_description IS NULL OR btrim(p_description) = '' THEN
        RAISE EXCEPTION 'Descrição inválida.';
    END IF;

    IF p_parameters IS NULL
       OR jsonb_typeof(p_parameters) <> 'object' THEN
        RAISE EXCEPTION 'Parâmetros inválidos.';
    END IF;

    IF p_action_hash IS NULL
       OR p_action_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Assinatura HMAC inválida.';
    END IF;


    INSERT INTO public.odin_approvals (
        execution_id,
        thread_id,
        step_id,
        action_type,
        description,
        parameters,
        action_hash,
        status
    )
    VALUES (
        p_execution_id,
        btrim(p_thread_id),
        p_step_id,
        btrim(p_action_type),
        btrim(p_description),
        p_parameters,
        p_action_hash,
        'pending'
    )
    RETURNING * INTO created_approval;


    INSERT INTO public.odin_audit_logs (
        event_type,
        execution_id,
        thread_id,
        actor,
        details
    )
    VALUES (
        'approval_requested',
        created_approval.execution_id,
        created_approval.thread_id,
        'ODIN',
        jsonb_build_object(
            'step_id', created_approval.step_id,
            'action_type', created_approval.action_type,
            'status', 'pending'
        )
    );

    RETURN NEXT created_approval;
    RETURN;

END;

$function$;


-- =====================================================
-- 3. REIVINDICAÇÃO SEGURA DA APROVAÇÃO
-- =====================================================

CREATE OR REPLACE FUNCTION public.odin_claim_approval_v2(
    p_execution_id uuid,
    p_thread_id text,
    p_step_id integer,
    p_action_type text,
    p_description text,
    p_parameters jsonb,
    p_action_hash text
)
RETURNS SETOF public.odin_approvals
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO ''
AS $function$

DECLARE
    claimed public.odin_approvals%ROWTYPE;

BEGIN

    IF p_execution_id IS NULL THEN
        RAISE EXCEPTION 'ID da execução inválido.';
    END IF;

    IF p_thread_id IS NULL OR btrim(p_thread_id) = '' THEN
        RAISE EXCEPTION 'Thread ID inválido.';
    END IF;

    IF p_step_id IS NULL OR p_step_id < 1 THEN
        RAISE EXCEPTION 'ID da etapa inválido.';
    END IF;

    IF p_action_type IS NULL OR btrim(p_action_type) = '' THEN
        RAISE EXCEPTION 'Tipo de ação inválido.';
    END IF;

    IF p_description IS NULL OR btrim(p_description) = '' THEN
        RAISE EXCEPTION 'Descrição inválida.';
    END IF;

    IF p_parameters IS NULL
       OR jsonb_typeof(p_parameters) <> 'object' THEN
        RAISE EXCEPTION 'Parâmetros inválidos.';
    END IF;

    IF p_action_hash IS NULL
       OR p_action_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'Assinatura HMAC inválida.';
    END IF;


    UPDATE public.odin_approvals AS a

    SET status = 'executing'

    WHERE a.execution_id = p_execution_id
      AND a.thread_id = btrim(p_thread_id)
      AND a.step_id = p_step_id
      AND a.action_type = btrim(p_action_type)
      AND a.description = btrim(p_description)
      AND a.parameters = p_parameters
      AND a.action_hash = p_action_hash
      AND a.status = 'approved'

    RETURNING a.* INTO claimed;


    IF NOT FOUND THEN
        RETURN;
    END IF;


    INSERT INTO public.odin_audit_logs (
        event_type,
        execution_id,
        thread_id,
        actor,
        details
    )
    VALUES (
        'approval_claimed',
        claimed.execution_id,
        claimed.thread_id,
        'ODIN',
        jsonb_build_object(
            'step_id', claimed.step_id,
            'action_type', claimed.action_type,
            'status', 'executing'
        )
    );


    RETURN NEXT claimed;
    RETURN;

END;

$function$;


-- =====================================================
-- 4. PERMISSÕES
-- =====================================================

REVOKE ALL ON FUNCTION public.odin_request_approval_v2(
    uuid, text, integer, text, text, text, jsonb
) FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.odin_claim_approval_v2(
    uuid, text, integer, text, text, jsonb, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.odin_request_approval_v2(
    uuid, text, integer, text, text, text, jsonb
) TO service_role;

GRANT EXECUTE ON FUNCTION public.odin_claim_approval_v2(
    uuid, text, integer, text, text, jsonb, text
) TO service_role;


NOTIFY pgrst, 'reload schema';

COMMIT;
