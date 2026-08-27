from datetime import datetime, timezone
from models import Meta, AvaliacaoFisica, Objetivo, NivelAtividade, db, StatusMetaEnum, select

# Dicionário de multiplicadores de atividade física
MULTIPLICADORES_ATIVIDADE = {
    NivelAtividade.SEDENTARIO: 1.2,
    NivelAtividade.LEVE: 1.375,
    NivelAtividade.MODERADO: 1.55,
    NivelAtividade.INTENSO: 1.725,
    NivelAtividade.MUITO_INTENSO: 1.9,
}


class MetaService:
    @staticmethod
    def _obter_fator_atividade(nivel: NivelAtividade) -> float:
        """Retorna o multiplicador numérico do nível de atividade."""
        if isinstance(nivel, str):
            try:
                nivel = NivelAtividade(nivel)
            except ValueError:
                return 1.2

        return MULTIPLICADORES_ATIVIDADE.get(nivel, 1.2)

    @staticmethod
    def calcular_metricas_meta(
        ultima_avaliacao: AvaliacaoFisica, objetivo: Objetivo
    ) -> tuple[float, float, float, float, float]:
        """Calcula calorias alvo, água diária e macronutrientes (proteínas, carboidratos e gorduras em gramas)

        baseando-se na última avaliação e no objetivo.
        """
        tmb = ultima_avaliacao.tmb or 0.0
        peso_atual = ultima_avaliacao.peso

        fator_atividade = MetaService._obter_fator_atividade(
            ultima_avaliacao.nivel_atividade_padrao
        )

        # Gasto Energético Total (GET)
        get = tmb * fator_atividade

        # Ajuste calórico e multiplicadores de macros por kg corporal
        if objetivo == Objetivo.EMAGRECER:
            calorias_alvo = get - 400.0  
            g_proteina_por_kg = 2.0
            g_gordura_por_kg = 0.9

        elif objetivo == Objetivo.GANHAR_MASSA:
            calorias_alvo = get + 300.0 
            g_proteina_por_kg = 2.0
            g_gordura_por_kg = 1.0
        else:  
            calorias_alvo = get
            g_proteina_por_kg = 1.6
            g_gordura_por_kg = 1.0

        # Meta de Água: 35 mL por quilo de peso corporal
        meta_agua_ml = peso_atual * 35.0

        # Cálculo das gramas de Proteína e Gordura
        proteinas_alvo_g = peso_atual * g_proteina_por_kg
        gorduras_alvo_g = peso_atual * g_gordura_por_kg

        # O restante do saldo calórico é convertido em Carboidratos (4 kcal por grama)
        calorias_proteinas = proteinas_alvo_g * 4.0
        calorias_gorduras = gorduras_alvo_g * 9.0
        calorias_restantes_carbo = calorias_alvo - (calorias_proteinas + calorias_gorduras)

        # Evita carboidrato negativo caso o déficit seja muito agressivo
        carboidratos_alvo_g = max(0.0, calorias_restantes_carbo / 4.0)

        return (
            round(calorias_alvo, 2),
            round(meta_agua_ml, 2),
            round(proteinas_alvo_g, 2),
            round(carboidratos_alvo_g, 2),
            round(gorduras_alvo_g, 2),
        )    


    @staticmethod
    def criar_meta(usuario_id: int, dados_validados: dict) -> tuple[dict | None, str | None]:
        """Cria uma nova meta calculando calorias e água a partir da última avaliação física."""
        # 1. Busca a última avaliação física ATIVA do usuário (desativado_em é Nulo)
        stmt_aval = (
            select(AvaliacaoFisica)
            .where(
                AvaliacaoFisica.usuario_id == usuario_id,
                AvaliacaoFisica.desativado_em.is_(None)
            )
            .order_by(AvaliacaoFisica.id.desc())
        )

        ultima_avaliacao = db.session.scalar(stmt_aval)

        if not ultima_avaliacao:
            return None, "Você precisa cadastrar ao menos uma avaliação física antes de definir uma meta."

        try:
            objetivo = dados_validados["objetivo"]
            peso_alvo = dados_validados["peso_alvo_kg"]

            # 2. Calcula calorias e água usando os dados da avaliação
            (
                calorias_alvo,
                meta_agua_ml,
                proteinas_alvo_g,
                carboidratos_alvo_g,
                gorduras_alvo_g,
            ) = MetaService.calcular_metricas_meta(ultima_avaliacao, objetivo)

            # 3. Desativa/Finaliza metas antigas que ainda estejam com status ATIVO
            stmt_metas_ativas = select(Meta).where(
                Meta.usuario_id == usuario_id,
                Meta.status == StatusMetaEnum.ATIVA
            )

            metas_ativas = db.session.scalars(stmt_metas_ativas).all()
            agora = datetime.now(timezone.utc)

            for meta_antiga in metas_ativas:
                meta_antiga.status = StatusMetaEnum.CONCLUIDA 
                meta_antiga.concluida_em = agora

            # 4. Instancia e salva a nova meta ativa
            nova_meta = Meta(
                usuario_id=usuario_id,
                avaliacao_origem_id=ultima_avaliacao.id,  
                objetivo=objetivo,
                peso_alvo_kg=peso_alvo,
                calorias_alvo_kcal=calorias_alvo,
                meta_agua_ml=meta_agua_ml,
                gorduras_alvo_g=gorduras_alvo_g,
                proteinas_alvo_g=proteinas_alvo_g,
                carboidratos_alvo_g=carboidratos_alvo_g,
                status=StatusMetaEnum.ATIVA
            )

            db.session.add(nova_meta)
            db.session.commit()

            return nova_meta.to_dict(), None

        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao criar meta: {str(e)}"

    @staticmethod
    def obter_meta_ativa(usuario_id: int) -> tuple[dict | None, str | None]:
        """Busca a meta ativa usando db.session.scalar (SQLAlchemy 2.0)."""
        stmt = select(Meta).where(
            Meta.usuario_id == usuario_id,
            Meta.status == StatusMetaEnum.ATIVA
        )
        
        meta = db.session.scalar(stmt)

        if not meta:
            return None, "Nenhuma meta ativa encontrada."
        
        return meta.to_dict(), None

    @staticmethod
    def obter_metas_concluidas(usuario_id: int) -> tuple[list[dict], str | None]:
        """Busca o histórico de todas as metas concluídas pelo usuário."""
        try:
            stmt = (
                db.select(Meta)
                .where(
                    Meta.usuario_id == usuario_id,
                    Meta.status == StatusMetaEnum.CONCLUIDA
                )
                .order_by(Meta.id.desc())
            )
            
            # db.session.scalars retorna a sequência de objetos Meta
            metas = db.session.scalars(stmt).all()

            if not metas:
                return None, "Nenhuma meta concluída foi encontrada."


            return [meta.to_dict() for meta in metas], None

        except Exception as e:
            return [], f"Erro ao buscar metas concluídas: {str(e)}"

    @staticmethod
    def atualizar_meta(meta_id: int, usuario_id: int, dados_validados: dict) -> tuple[dict | None, str | None]:
        """Atualiza a meta pontualmente e recalcula métricas se o objetivo mudar."""
        stmt = select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id
        )

        meta = db.session.scalar(stmt)

        if not meta:
            return None, "Meta não encontrada."

        try:
            if "peso_alvo_kg" in dados_validados:
                meta.peso_alvo_kg = dados_validados["peso_alvo_kg"]

            if "objetivo" in dados_validados:
                novo_objetivo = dados_validados["objetivo"]
                meta.objetivo = novo_objetivo

                # Busca avaliação mais recente para recalcular o GET/Água
                stmt_aval = (
                    select(AvaliacaoFisica)
                    .where(
                        AvaliacaoFisica.usuario_id == usuario_id,
                        AvaliacaoFisica.desativado_em.is_(None)
                    )
                    .order_by(AvaliacaoFisica.id.desc())
                )
                ultima_avaliacao = db.session.scalar(stmt_aval)

                if ultima_avaliacao:
                    calorias_alvo, meta_agua_ml, carboidratos_alvo_g, proteinas_alvo_g, gorduras_alvo_g  = MetaService.calcular_metricas_meta(
                        ultima_avaliacao, novo_objetivo
                    )
                    meta.calorias_alvo_kcal = calorias_alvo
                    meta.meta_agua_ml = meta_agua_ml
                    meta.carboidratos_alvo_g = carboidratos_alvo_g
                    meta.proteinas_alvo_g = proteinas_alvo_g
                    meta.gorduras_alvo_g = gorduras_alvo_g

            db.session.commit()
            return meta.to_dict(), None

        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao atualizar meta: {str(e)}"

    @staticmethod
    def concluir_meta(meta_id: int, usuario_id: int) -> tuple[dict | None, str | None]:
        """Marca uma meta ativa como CONCLUIDA."""
        stmt = db.select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id
        )
        meta = db.session.scalar(stmt)

        if not meta:
            return None, "Meta não encontrada."

        if meta.status != StatusMetaEnum.ATIVA:
            return None, f"Apenas metas ativas podem ser concluídas. Status atual: {meta.status.value}."

        try:
            meta.status = StatusMetaEnum.CONCLUIDA
            db.session.commit()
            return meta.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao concluir meta: {str(e)}"

    @staticmethod
    def deletar_meta(meta_id: int, usuario_id: int) -> tuple[bool, str | None]:
        """Deleta uma meta inativa."""
        stmt = select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id
        )

        meta = db.session.scalar(stmt)

        if not meta:
            return False, "Meta não encontrada."

        if meta.status == StatusMetaEnum.ATIVA:
            return False, "Não é permitido excluir uma meta ativa. Finalize ou cancele a meta antes de excluir."

        try:
            db.session.delete(meta)
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            return False, f"Erro ao deletar meta: {str(e)}"
    

    @staticmethod
    def cancelar_meta(meta_id: int, usuario_id: int) -> tuple[dict | None, str | None]:
        """Marca uma meta ativa como CANCELADA."""
        stmt = db.select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id
        )
        meta = db.session.scalar(stmt)

        if not meta:
            return None, "Meta não encontrada."

        if meta.status != StatusMetaEnum.ATIVA:
            return None, f"Apenas metas ativas podem ser canceladas. Status atual: {meta.status.value}."

        try:
            meta.status = StatusMetaEnum.CANCELADA
            db.session.commit()
            return meta.to_dict(), None
        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao cancelar meta: {str(e)}"