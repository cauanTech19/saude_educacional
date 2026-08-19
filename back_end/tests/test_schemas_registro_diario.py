from datetime import date
import pytest
from pydantic import ValidationError
from schemas.registro_diario import RegistroDiarioBase, RegistroDiarioUpdateSchema


class TestRegistroDiarioBaseSchema:
    def test_instanciacao_com_sucesso_dados_validos(self):
        """Valida que o schema aceita valores dentro dos limites estabelecidos."""
        dados = {
            "data": date(2026, 8, 19),
            "calorias_consumidas_kcal": 2200.5,
            "proteinas_g": 160.0,
            "carboidratos_g": 250.0,
            "gorduras_g": 70.0,
            "agua_consumida_ml": 3000.0,
            "exercicio_realizado": True,
            "peso_registro_kg": 80.5,
            "observacoes": "Treino intenso e boa hidratação.",
        }
        schema = RegistroDiarioBase(**dados)

        assert schema.data == date(2026, 8, 19)
        assert schema.calorias_consumidas_kcal == 2200.5
        assert schema.proteinas_g == 160.0
        assert schema.exercicio_realizado is True
        assert schema.peso_registro_kg == 80.5

    def test_valores_default_e_opcionais(self):
        """Garante que todos os campos nutricionais aceitam None e a data assume a factory padrão."""
        schema = RegistroDiarioBase()

        assert schema.data == date.today()
        assert schema.calorias_consumidas_kcal is None
        assert schema.proteinas_g is None
        assert schema.carboidratos_g is None
        assert schema.gorduras_g is None
        assert schema.agua_consumida_ml is None
        assert schema.exercicio_realizado is None
        assert schema.peso_registro_kg is None
        assert schema.observacoes is None

    @pytest.mark.parametrize(
        "campo,valor_invalido",
        [
            # Limites de Calorias (0.0 a 15000.0)
            ("calorias_consumidas_kcal", -0.1),
            ("calorias_consumidas_kcal", 15000.1),
            # Limites de Proteínas (0.0 a 600.0)
            ("proteinas_g", -1.0),
            ("proteinas_g", 600.1),
            # Limites de Carboidratos (0.0 a 1500.0)
            ("carboidratos_g", -0.5),
            ("carboidratos_g", 1500.1),
            # Limites de Gorduras (0.0 a 500.0)
            ("gorduras_g", -0.1),
            ("gorduras_g", 500.1),
            # Limites de Água (0.0 a 10000.0)
            ("agua_consumida_ml", -100.0),
            ("agua_consumida_ml", 10000.1),
            # Limites de Peso (20.0 a 350.0)
            ("peso_registro_kg", 19.9),
            ("peso_registro_kg", 350.1),
            # Limite de Tamanho de Observações (max 255 chars)
            ("observacoes", "a" * 256),
        ],
    )
    def test_rejeita_valores_fora_dos_limites(self, campo, valor_invalido):
        """Testa o disparo de ValidationError ao ultrapassar os limites ge/le/max_length."""
        dados = {campo: valor_invalido}
        with pytest.raises(ValidationError):
            RegistroDiarioBase(**dados)


class TestRegistroDiarioUpdateSchema:

    def test_update_schema_permite_data_como_none(self):
        """Valida que o RegistroDiarioUpdateSchema sobrescreve o default_factory de data para None."""
        schema = RegistroDiarioUpdateSchema()
        assert schema.data is None

    def test_update_schema_mantem_limites_da_classe_base(self):
        """Garante que a herança do RegistroDiarioUpdateSchema preserva as validações ge/le."""
        with pytest.raises(ValidationError):
            RegistroDiarioUpdateSchema(peso_registro_kg=400.0)

        with pytest.raises(ValidationError):
            RegistroDiarioUpdateSchema(agua_consumida_ml=-50.0)

        # Envio válido parcial
        schema = RegistroDiarioUpdateSchema(agua_consumida_ml=2000.0)
        assert schema.agua_consumida_ml == 2000.0
        assert schema.calorias_consumidas_kcal is None