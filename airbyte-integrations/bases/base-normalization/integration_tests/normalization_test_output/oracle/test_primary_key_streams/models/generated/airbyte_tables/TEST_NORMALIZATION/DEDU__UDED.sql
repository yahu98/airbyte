{{ config(schema="TEST_NORMALIZATION", tags=["top-level"]) }}
-- Final base SQL model
select
    ID,
    NAME,
    _AB____LSN,
    _AB___D_AT,
    _AB___AT_1,
    _airbyte_emitted_at,
    _AIR__SHID
from {{ ref('DEDU__UDED_SCD') }}
-- DEDU__UDED from {{ source('TEST_NORMALIZATION', '_AIRBYTE_RAW_DEDUP_CDC_EXCLUDED') }}
where _airbyte_active_row = True

