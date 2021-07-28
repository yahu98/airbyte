{{ config(schema="_AIRBYTE_TEST_NORMALIZATION", tags=["nested-intermediate"]) }}
-- SQL model to build a hash column based on the values of this record
select
    *,
    {{ dbt_utils.surrogate_key([
        '_AIR__SHID',
        'ID',
    ]) }} as _AIR__SHID
from {{ ref('NESTED_STR_A1B_DOUB__DATA_AB2') }}
-- DOUB__DATA at nested_stream_with_complex_columns_resulting_into_long_names/partition/double_array_data

