import pytest
from pydantic import ValidationError
from schemas.registro_diario import RegistroDiarioCreateSchema, RegistroDiarioUpdateSchema


class TestRegistroDiarioCreateSchema:
    def test_criacao_com_sucesso_meta_id_obrigatorio(self):
        """Garante a instanciação correta fornecendo o meta_id obrigatório."""
        schema = RegistroDiarioCreateSchema(
            meta_id=1,
            calorias_consumidas_kcal=2000.0,
            agua_consumida_ml=3000.0
        )
        assert schema.meta_id == 1
        assert schema.calorias_consumidas_kcal == 2000.0

    def test_criacao_falha_sem_meta_id(self):
        """Bloqueia a criação caso o meta_id não seja informado."""
        with pytest.raises(ValidationError) as exc_info:
            RegistroDiarioCreateSchema(calorias_consumidas_kcal=2000.0)
        
        assert any(err["loc"] == ("meta_id",) for err in exc_info.value.errors())

    @pytest.mark.parametrize("meta_id_invalido", [0, -1])
    def test_criacao_falha_meta_id_invalido(self, meta_id_invalido):
        """Rejeita meta_id <= 0."""
        with pytest.raises(ValidationError):
            RegistroDiarioCreateSchema(meta_id=meta_id_invalido)


class TestRegistroDiarioUpdateSchema:
    def test_update_valida_limites_nutricionais(self):
        """Mantenha as validações sanitárias ativas durante atualizações parciais."""
        schema = RegistroDiarioUpdateSchema(proteinas_g=150.0)
        assert schema.proteinas_g == 150.0

        with pytest.raises(ValidationError):
            RegistroDiarioUpdateSchema(calorias_consumidas_kcal=20000.0)