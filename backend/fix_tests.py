file_path = r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\modules\liquidaciones\tests\integration\test_hu_nueva_liquidacion.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Cambiar el import a sync Client
content = content.replace("from django.test import AsyncClient", "from django.test import Client")

# Cambiar el fixture del api_client a sync
content = content.replace(
    "@pytest.fixture\ndef api_client(db):\n    \"\"\"Django AsyncClient for testing Ninja endpoints.\"\"\"\n    return Client()",
    "@pytest.fixture\ndef api_client(db):\n    \"\"\"Django Client (sync) for testing Ninja endpoints.\"\"\"\n    return Client()"
)

# Cambiar los 3 tests que importan de async a sync
# Solo los 3 que importan (los 2 que validan area son diferentes)
import re

# Reemplazar los 3 tests específicos que tienen el patrón con async/await
# Test 1: happy_path
content = content.replace(
    "@pytest.mark.asyncio\nasync def test_hu_nueva_liquidacion_happy_path(",
    "def test_hu_nueva_liquidacion_happy_path("
)
content = content.replace(
    "    response = await api_client.post(",
    "    response = api_client.post("
)

# Test 2: response_has_three_wrappers
content = content.replace(
    "@pytest.mark.asyncio\nasync def test_hu_nueva_liquidacion_response_has_three_wrappers(",
    "def test_hu_nueva_liquidacion_response_has_three_wrappers("
)

# Test 3: no_usuario_creador_in_input
content = content.replace(
    "@pytest.mark.asyncio\nasync def test_hu_nueva_liquidacion_no_usuario_creador_in_input(",
    "def test_hu_nueva_liquidacion_no_usuario_creador_in_input("
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Cambios aplicados")
