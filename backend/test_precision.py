import json
from decimal import Decimal

data = json.loads('{"pct": 0.00015}')
pct_json = data['pct']
print('JSON float repr:', repr(pct_json))
print('JSON float value:', pct_json)
print('As string:', str(pct_json))
print('As Decimal from str:', Decimal(str(pct_json)))
print('Direct Decimal:', Decimal('0.00015'))
print()
print('Are they equal?', Decimal(str(pct_json)) == Decimal('0.00015'))

# Test with our actual JSON
data2 = json.load(open('modules/liquidaciones/seeds/tarifas_edificacion.json'))
for i, t in enumerate(data2['tarifas']):
    pct_raw = t['porcentaje_liquidacion']
    pct_via_float = Decimal(str(pct_raw))
    print(f'Entry {i}: raw={repr(pct_raw)} via_float={pct_via_float} direct=Decimal({repr(pct_raw)})')
