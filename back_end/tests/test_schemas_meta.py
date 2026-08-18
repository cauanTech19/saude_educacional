import pytest
from pydantic import ValidationError
from models import Objetivo
from schemas.meta import MetaCreateSchema, MetaUpdateSchema


class TestMetaCreateSchema:
    """Testes de unidade para o MetaCreateSchema (Criação de Metas)."""

    def test_meta_create_schema_sucesso(self):
        """Deve validar com sucesso quando todos os campos estiverem corretos."""
        payload = {
            "objetivo": "emagrecer",
            "peso_alvo_kg": 75.0
        }
        schema = MetaCreateSchema(**payload)

        assert schema.objetivo == Objetivo.EMAGRECER
        assert schema.peso_alvo_kg == 75.0

    @pytest.mark.parametrize("objetivo_valido", ["emagrecer", "manter", "ganhar_massa"])
    def test_meta_create_schema_objetivos_validos(self, objetivo_valido):
        """Deve aceitar todas as opções válidas do Enum Objetivo."""
        payload = {
            "objetivo": objetivo_valido,
            "peso_alvo_kg": 70.0
        }
        schema = MetaCreateSchema(**payload)
        assert schema.objetivo.value == objetivo_valido

    def test_meta_create_schema_objetivo_invalido(self):
        """Deve levantar ValidationError se o objetivo não existir no Enum."""
        payload = {
            "objetivo": "ficar_monstro",
            "peso_alvo_kg": 80.0
        }
        with pytest.raises(ValidationError) as exc_info:
            MetaCreateSchema(**payload)

        assert "objetivo" in str(exc_info.value)

    @pytest.mark.parametrize("peso_invalido", [15.0, 20.0, 500.0, 700.0])
    def test_meta_create_schema_peso_fora_dos_limites(self, peso_invalido):
        """Deve levantar ValidationError se o peso for <= 20kg ou >= 350kg."""
        payload = {
            "objetivo": "emagrecer",
            "peso_alvo_kg": peso_invalido
        }
        with pytest.raises(ValidationError) as exc_info:
            MetaCreateSchema(**payload)

        assert "peso_alvo_kg" in str(exc_info.value)

    def test_meta_create_schema_campos_extras_proibidos(self):
        """Deve barrar e lançar erro se o payload contiver chaves não declaradas (extra='forbid')."""
        payload = {
            "objetivo": "emagrecer",
            "peso_alvo_kg": 70.0,
            "calorias_alvo_kcal": 2000.0  # Campo extra que não deve vir no Create
        }
        with pytest.raises(ValidationError) as exc_info:
            MetaCreateSchema(**payload)

        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestMetaUpdateSchema:
    """Testes de unidade para o MetaUpdateSchema (Atualização de Metas)."""

    def test_meta_update_schema_sucesso_parcial(self):
        """Deve permitir a atualização enviando apenas um dos campos."""
        payload = {"peso_alvo_kg": 82.5}
        schema = MetaUpdateSchema(**payload)

        dados = schema.model_dump(exclude_unset=True)
        assert dados == {"peso_alvo_kg": 82.5}
        assert schema.objetivo is None

    def test_meta_update_schema_vazio(self):
        """Deve instanciar sem erros com payload vazio {}, deixando os campos como None."""
        schema = MetaUpdateSchema()
        dados = schema.model_dump(exclude_unset=True)

        assert dados == {}
        assert schema.objetivo is None
        assert schema.peso_alvo_kg is None

    def test_meta_update_schema_campos_extras_proibidos(self):
        """Deve proibir chaves extras também na atualização."""
        payload = {"chave_invalida": 123}
        with pytest.raises(ValidationError) as exc_info:
            MetaUpdateSchema(**payload)

        assert "Extra inputs are not permitted" in str(exc_info.value)