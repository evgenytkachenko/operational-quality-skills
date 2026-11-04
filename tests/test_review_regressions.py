import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from operational_quality.core import Config, analyze, normalize, redact, source_instant
from operational_quality.inquiry import local_assessment, validate_assessment
from test_investigation import ROOT, packet_for, config, fixture, draft


@pytest.mark.parametrize('text,secret',[
    ('Authorization: Bearer abc123', 'abc123'),
    ('Authorization: Basic dXNlcjpwYXNz', 'dXNlcjpwYXNz'),
    ('{"password": "secret123"}', 'secret123'),
    ('{"api_key":"key123"}', 'key123'),
    ('{"token":"escaped\\"secret"}', 'secret'),
])
def test_common_secret_formats(config,fixture,text,secret):
    fixture['workflow']['rows'][0]['message']=text
    packet=packet_for(config,fixture)
    assert secret not in json.dumps(packet)
    assert redact(redact(text))==redact(text)


def test_unicode_escape_does_not_bypass_output_check(config,fixture,draft):
    data=json.loads(draft)
    data['unknowns'].append('person@example.com')
    raw=json.dumps(data).replace('@',r'\u0040')
    with pytest.raises(ValueError,match='sensitive'):
        validate_assessment(raw,packet_for(config,fixture))


def test_empty_evidence_can_produce_honest_unknown(config):
    packet=analyze(config,lambda *args:([],[]))
    hypotheses=[dict(explanation=e,status='unknown',supporting=[],contradicting=[],discriminating_check='Obtain authorized workflow history.',counterfactual='Unknown without records.') for e in ['Routing mismatch','Capacity shortage']]
    report=validate_assessment(json.dumps(dict(observations=[],hypotheses=hypotheses,controls=[],unknowns=['No usable evidence available.'])),packet)
    assert report['assessment']['observations']==[]


@pytest.mark.parametrize('model',['example:cloud','example-cloud'])
def test_cloud_model_selectors_rejected(config,fixture,model):
    client=MagicMock()
    with pytest.raises(ValueError,match='cloud'):
        local_assessment(packet_for(config,fixture),model,client)
    client.chat.assert_not_called()


def test_record_id_and_case_id_are_distinct(config,fixture):
    opaque='A'*150+'/span:record=='
    fixture['workflow']['rows'][0]['id']=opaque
    packet=packet_for(config,fixture)
    assert any(e['ref']=='workflow:'+opaque for e in packet['events'])
    fixture['workflow']['rows'][0]['id']=42
    assert any(e['ref']=='workflow:42' for e in packet_for(config,fixture)['events'])


@pytest.mark.parametrize('encoding,value', [('epoch_s',1790841600),('epoch_ms',1790841600000),('epoch_ns',1790841600000000000)])
def test_explicit_epoch_units(encoding,value):
    assert source_instant(value,encoding)==datetime(2026,10,1,8,tzinfo=timezone.utc)
    with pytest.raises(ValueError): source_instant(str(value),encoding)


@pytest.mark.parametrize('index,model_module,model_name',[
    (1,'logs_list_response','LogsListResponse'),
    (2,'spans_list_response','SpansListResponse'),
    (3,'events_list_response','EventsListResponse'),
])
def test_real_sdk_response_deserialization(config,fixture,index,model_module,model_name):
    import importlib
    from datadog_api_client import ApiClient, Configuration
    model=getattr(importlib.import_module('datadog_api_client.v2.model.'+model_module),model_name)
    source=config.sources[index]
    # Exercise real installed SDK response schemas, not a log-shaped common fake.
    with ApiClient(Configuration()) as client:
        parsed=client.deserialize(json.dumps({'data':fixture[source.name]['rows']}),(model,),True).to_dict()
    events,notes=normalize(config,source,parsed['data'])
    assert len(events)==len(fixture[source.name]['rows']) and not notes
    assert events[0]['case_id']=='INV-104'
    assert events[0]['message']


def test_invalid_model_argument_is_rejected(config,fixture):
    with pytest.raises(ValueError,match='model name'):
        local_assessment(packet_for(config,fixture),None,MagicMock())


def test_postgres_rejects_epoch_columns(config):
    data=config.model_dump()
    data['sources'][0]['timestamp_format']='epoch_ms'
    with pytest.raises(ValueError,match='timezone-aware timestamp column'):
        Config.model_validate(data)
