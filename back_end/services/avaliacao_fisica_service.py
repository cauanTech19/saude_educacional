from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from models import AvaliacaoFisica, NivelAtividade, Usuario, db, SexoBiologico, select, StatusAvaliacaoEnum


class AvaliacaoService:
    @staticmethod
    def calcular_imc(peso: float, altura: float) -> float:
        """Calcula o Índice de Massa Corporal (IMC).
        
        Fórmula: peso / (altura * altura)
        """
        if altura <= 0:
            raise ValueError('Altura deve ser maior que zero.')
        return round(peso / (altura ** 2), 2)

    @staticmethod
    def classificar_imc(imc: float) -> str:
        """Retorna a classificação oficial da OMS com base no IMC."""
        if imc < 18.5:
            return 'Abaixo do peso'
        if imc < 25.0:
            return 'Peso normal'
        if imc < 30.0:
            return 'Sobrepeso'
        if imc < 35.0:
            return 'Obesidade Grau I'
        if imc < 40.0:
            return 'Obesidade Grau II'
        return 'Obesidade Grau III'

    @staticmethod
    def calcular_tmb(peso: float, altura_m: float, idade: int, sexo: Optional[str] = 'M') -> float:
        """Calcula a Taxa Metabólica Basal (TMB) pela equação de Mifflin-St Jeor."""
        altura_cm = altura_m * 100.0

        sexo_str = (
            sexo.value.upper() if hasattr(sexo, 'value') else str(sexo or 'M').upper()
        )

        # Mifflin-St Jeor: (10 * peso) + (6.25 * altura_cm) - (5 * idade) + s
        if sexo_str in ['F', 'FEMININO']:
            tmb = (10.0 * peso) + (6.25 * altura_cm) - (5.0 * idade) - 161.0
        else:
            tmb = (10.0 * peso) + (6.25 * altura_cm) - (5.0 * idade) + 5.0

        return round(tmb, 2)

    @staticmethod
    def calcular_meta_deficit_calorico(
        tmb: float,
        fator_atividade: float = 1.2,
        deficit_desejado: float = 500.0,
    ) -> Dict[str, float]:
        """Calcula o Gasto Calórico Total Diário (TDEE) e a meta recomendada de calorias."""
        gasto_total = tmb * fator_atividade
        meta_calorias = max(1200.0, gasto_total - deficit_desejado)

        return {
            'tmb': tmb,
            'gasto_total_diario': round(gasto_total, 2),
            'meta_calorias_deficit': round(meta_calorias, 2),
            'deficit_diario': round(gasto_total - meta_calorias, 2),
        }

    @staticmethod
    def criar_avaliacao(usuario_id: int, dados_validados: dict) -> Tuple[Optional[dict], Optional[str]]:
        """Recebe os dados validados, calcula IMC e TMB e persiste no banco."""
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
          return None, 'Usuário não encontrado.'

        peso = dados_validados['peso']
        altura = dados_validados['altura']
        
        # Garante a conversão do Enum
        sexo_input = dados_validados['sexo_biologico']
        sexo_enum = sexo_input if isinstance(sexo_input, SexoBiologico) else SexoBiologico(sexo_input)

        # 1. Cálculos dinâmicos
        imc = AvaliacaoService.calcular_imc(peso, altura)
        
        tmb = AvaliacaoService.calcular_tmb(
            peso=peso,
            altura_m=altura,
            idade=usuario.idade_atual,
            sexo=sexo_enum,
        )

        # 2. Instancia a Avaliação Física
        nova_avaliacao = AvaliacaoFisica(
            usuario_id=usuario_id,
            peso=peso,
            altura=altura,
            sexo_biologico=sexo_enum,
            imc=imc,
            tmb=tmb,
            nivel_atividade_padrao=dados_validados.get(
                'nivel_atividade_padrao', NivelAtividade.SEDENTARIO
            ),
            cintura=dados_validados.get('cintura'),
            quadril=dados_validados.get('quadril'),
            braco_relaxado=dados_validados.get('braco_relaxado'),
            braco_contraido=dados_validados.get('braco_contraido'),
        )

        try:
            db.session.add(nova_avaliacao)
            db.session.commit()
            return nova_avaliacao, None
        except Exception as e:
            db.session.rollback()
            return None, f'Erro ao salvar avaliação física no banco: {str(e)}'

    @staticmethod
    def listar_avaliacoes_usuario(usuario_id: int, apenas_ativas: bool = True) -> List[dict]:
        """Retorna o histórico de avaliações do usuário em formato dict (por padrão exclui deletadas)."""
        stmt = select(AvaliacaoFisica).where(AvaliacaoFisica.usuario_id == usuario_id)

        if apenas_ativas:
          stmt = stmt.where(AvaliacaoFisica.desativado_em.is_(None))

        stmt = stmt.order_by(AvaliacaoFisica.data_criacao.desc())
        avaliacoes = db.session.scalars(stmt).all()

        return [a.to_dict() for a in avaliacoes]

    @staticmethod
    def atualizar_avaliacao(avaliacao_id: int, usuario_id: int, dados_validados: dict) -> Tuple[Optional[dict], Optional[str]]:
        """Atualiza uma avaliação ativa, garantindo apenas os campos permitidos e recalcula IMC e TMB."""
        stmt = select(AvaliacaoFisica).where(
            AvaliacaoFisica.id == avaliacao_id,
            AvaliacaoFisica.usuario_id == usuario_id,
            AvaliacaoFisica.desativado_em.is_(None)
        )
        avaliacao = db.session.scalar(stmt)

        if not avaliacao:
            return None, 'Avaliação não encontrada ou desativada.'

        CAMPOS_PERMITIDOS = {
            'peso',
            'altura',
            'sexo_biologico',
            'nivel_atividade_padrao',
            'cintura',
            'quadril',
            'braco_relaxado',
            'braco_contraido',
        }

        for chave, valor in dados_validados.items():
            if chave in CAMPOS_PERMITIDOS and valor is not None:
                setattr(avaliacao, chave, valor)

        # Recalcula IMC e TMB
        avaliacao.imc = AvaliacaoService.calcular_imc(avaliacao.peso, avaliacao.altura)
        avaliacao.tmb = AvaliacaoService.calcular_tmb(
            peso=avaliacao.peso,
            altura_m=avaliacao.altura,
            idade=avaliacao.usuario.idade_atual,
            sexo=avaliacao.sexo_biologico,
        )

        try:
            db.session.commit()
            return avaliacao, None
        except Exception as e:
            db.session.rollback()
            return None, f'Erro ao atualizar avaliação no banco: {str(e)}'

    @staticmethod
    def ativar_avaliacao(avaliacao_id: int, usuario_id: int) -> Tuple[Optional[dict], Optional[str]]:
        """Reativa uma avaliação física previamente desativada (remove soft delete)."""
        stmt = select(AvaliacaoFisica).where(
            AvaliacaoFisica.id == avaliacao_id,
            AvaliacaoFisica.usuario_id == usuario_id,
            AvaliacaoFisica.desativado_em.is_not(None)
        )
        avaliacao = db.session.scalar(stmt)

        if not avaliacao:
          return None, 'Avaliação não encontrada ou já está ativa.'

        avaliacao.desativado_em = None
        avaliacao.ativo = StatusAvaliacaoEnum.ATIVO

        try:
          db.session.commit()
          return avaliacao, None
        except Exception as e:
          db.session.rollback()
          return None, f'Erro ao reativar avaliação no banco: {str(e)}'

    @staticmethod
    def desativar_avaliacao(avaliacao_id: int, usuario_id: int) -> Tuple[bool, Optional[str]]:
        """Executa o soft delete da avaliação preenchendo desativado_em."""
        stmt = select(AvaliacaoFisica).where(
            AvaliacaoFisica.id == avaliacao_id,
            AvaliacaoFisica.usuario_id == usuario_id,
            # Pode verificar pelo status ativo ou se desativado_em é Nulo
            AvaliacaoFisica.ativo == StatusAvaliacaoEnum.ATIVO 
        )
        avaliacao = db.session.scalar(stmt)

        if not avaliacao:
            return False, 'Avaliação não encontrada ou já desativada.'

        avaliacao.desativado_em = datetime.now(timezone.utc)
        avaliacao.ativo = StatusAvaliacaoEnum.DESATIVADO

        try:
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f'Erro ao desativar avaliação no banco: {str(e)}'