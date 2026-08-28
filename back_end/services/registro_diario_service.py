from typing import Dict, Any
from models import Objetivo, Meta, select, RegistroDiario, db
from schemas.registro_diario import RegistroDiarioCreateSchema, RegistroDiarioBase, RegistroDiarioUpdateSchema
from datetime import date
from typing import Optional


class RegistroDiarioService:
    @classmethod
    def criar_registro(cls, usuario_id: int, dados: RegistroDiarioCreateSchema
    ) -> Dict[str, Any]:
        """Cria um novo registro diário e o vincula à meta ativa."""
        # 1. Busca a meta usando select e where
        stmt = select(Meta).where(
            Meta.id == dados.meta_id,
            Meta.usuario_id == usuario_id
        )
        meta = db.session.execute(stmt).scalar_one_or_none()

        if not meta:
            raise ValueError("Meta não encontrada ou não pertence ao usuário.")

        # 2. Instancia e persiste a nova entidade
        novo_registro = RegistroDiario(
            usuario_id=usuario_id,
            meta_id=dados.meta_id,
            data=date.today(),
            calorias_consumidas_kcal=dados.calorias_consumidas_kcal,
            proteinas_g=dados.proteinas_g,
            carboidratos_g=dados.carboidratos_g,
            gorduras_g=dados.gorduras_g,
            agua_consumida_ml=dados.agua_consumida_ml,
            exercicio_realizado=dados.exercicio_realizado,
            peso_registro_kg=dados.peso_registro_kg,
            observacoes=dados.observacoes
        )

        db.session.add(novo_registro)
        db.session.commit()
        db.session.refresh(novo_registro)

        # 3. Processa o feedback
        feedback = cls.gerar_feedback_diario(novo_registro, meta)

        return {
            "registro": novo_registro,
            "feedback": feedback
        }

    @classmethod
    def buscar_por_id(cls, usuario_id: int, registro_id: int) -> Optional[RegistroDiario]:
        """Busca um registro específico garantindo o escopo do usuário."""
        stmt = select(RegistroDiario).where(
            RegistroDiario.id == registro_id,
            RegistroDiario.usuario_id == usuario_id
        )
        return db.session.execute(stmt).scalar_one_or_none()


    @classmethod
    def atualizar_registro(cls, usuario_id: int, registro_id: int, dados: RegistroDiarioUpdateSchema
    ) -> Dict[str, Any]:
        """Atualiza parcialmente as métricas do dia sem alterar a meta vinculada."""
        
        registro = cls.buscar_por_id(usuario_id, registro_id)
        if not registro:
            raise ValueError("Registro diário não encontrado.")
        

        dados_dict = dados.model_dump(exclude_unset=True)
        for campo, valor in dados_dict.items():
            setattr(registro, campo, valor)
            
        db.session.commit()
        db.session.refresh(registro)

        stmt_meta = select(Meta).where(Meta.id == registro.meta_id)
        meta = db.session.execute(stmt_meta).scalar_one_or_none()

        feedback = cls.gerar_feedback_diario(registro, meta)

        return {
            "registro": registro,
            "feedback": feedback
        }

    @classmethod
    def deletar_registro(cls, usuario_id: int, registro_id: int) -> bool:
        """Deleta fisicamente um registro diário garantindo o escopo do usuário."""
        registro = cls.buscar_por_id(usuario_id, registro_id)
        if not registro:
            return False

        db.session.delete(registro)
        db.session.commit()
        return True


    @classmethod
    def avaliar_ganho_massa(cls, registro, meta) -> Dict[str, Any]:
        """Regra para Hipertrofia: Foco em proteínas, superávit e carboidratos para energia."""
        bateu_proteina = (registro.proteinas_g or 0) >= (meta.proteinas_alvo_g or 0)
        bateu_calorias = (registro.calorias_consumidas_kcal or 0) >= (meta.calorias_alvo_kcal or 0)
        bateu_carbo = (registro.carboidratos_g or 0) >= (meta.carboidratos_alvo_g or 0)
        bateu_agua = (registro.agua_consumida_ml or 0) >= (meta.meta_agua_ml or 0)

        alertas = []
        if not bateu_proteina:
            alertas.append("faltou proteína para reconstrução muscular")

        if not bateu_calorias:
            alertas.append("calorias abaixo do necessário para hipertrofia")

        if not bateu_carbo:
            alertas.append("carboidratos baixos para rendimento do treino")

        if not bateu_agua:
            alertas.append("meta de água não atingida")

        sucesso = bateu_proteina and bateu_calorias and bateu_agua

        return {
            "objetivo": Objetivo.GANHAR_MASSA,
            "sucesso": sucesso,
            "mensagem": "Excelente dia para ganho de massa!" if sucesso else f"Atenção: {', '.join(alertas)}.",
            "detalhes": {
                "proteina_ok": bateu_proteina,
                "calorias_ok": bateu_calorias,
                "carbo_ok": bateu_carbo,
                "agua_ok": bateu_agua
            }
        }

    @classmethod
    def avaliar_emagrecimento(cls, registro, meta) -> Dict[str, Any]:
        """Regra para Déficit: Não estourar calorias nem gorduras, mantendo proteína e água."""
        calorias_ok = (registro.calorias_consumidas_kcal or 0) <= (meta.calorias_alvo_kcal or 0)
        gorduras_ok = (registro.gorduras_g or 0) <= (meta.gorduras_alvo_g or 0) if meta.gorduras_alvo_g else True
        proteina_ok = (registro.proteinas_g or 0) >= (meta.proteinas_alvo_g or 0)
        agua_ok = (registro.agua_consumida_ml or 0) >= (meta.meta_agua_ml or 0)

        alertas = []
        if not calorias_ok:
            alertas.append("ultrapassou o teto calórico")

        if not gorduras_ok:
            alertas.append("gorduras acima do teto planejado")

        if not proteina_ok:
            alertas.append("proteína baixa (risco de perder massa magra)")

        if not agua_ok:
            alertas.append("água abaixo da meta")

        sucesso = calorias_ok and proteina_ok and agua_ok

        return {
            "objetivo": Objetivo.EMAGRECER,
            "sucesso": sucesso,
            "mensagem": "Déficit calórico mantido com sucesso!" if sucesso else f"Atenção: {', '.join(alertas)}.",
            "detalhes": {
                "calorias_ok": calorias_ok,
                "gorduras_ok": gorduras_ok,
                "proteina_ok": proteina_ok,
                "agua_ok": agua_ok
            }
        }

    @classmethod
    def avaliar_manutencao(cls, registro, meta) -> Dict[str, Any]:
        """Regra para Manutenção: Equilíbrio geral próximo das metas estipuladas."""
        calorias_consumidas = registro.calorias_consumidas_kcal or 0
        calorias_alvo = meta.calorias_alvo_kcal or 0

        calorias_ok = (calorias_alvo * 0.95) <= calorias_consumidas <= (calorias_alvo * 1.05)
        proteina_ok = (registro.proteinas_g or 0) >= (meta.proteinas_alvo_g or 0)
        agua_ok = (registro.agua_consumida_ml or 0) >= (meta.meta_agua_ml or 0)

        alertas = []
        if not calorias_ok:
            if calorias_consumidas > calorias_alvo * 1.05:
                alertas.append("calorias muito acima da manutenção")
            else:
                alertas.append("calorias muito abaixo da manutenção")

        if not proteina_ok:
            alertas.append("proteínas abaixo do alvo")

        if not agua_ok:
            alertas.append("meta de água não atingida")

        sucesso = calorias_ok and proteina_ok and agua_ok

        return {
            "objetivo": Objetivo.MANTER,
            "sucesso": sucesso,
            "mensagem": "Balanço mantido no alvo de manutenção!" if sucesso else f"Atenção: {', '.join(alertas)}.",
            "detalhes": {
                "calorias_ok": calorias_ok,
                "proteina_ok": proteina_ok,
                "agua_ok": agua_ok
            }
        }

    @classmethod
    def gerar_feedback_diario(cls, registro, meta) -> Dict[str, Any]:
        """Roteador principal baseado no objetivo cadastrado na meta."""
        if meta.objetivo == Objetivo.GANHAR_MASSA:
            return cls.avaliar_ganho_massa(registro, meta)
        elif meta.objetivo == Objetivo.EMAGRECER:
            return cls.avaliar_emagrecimento(registro, meta)
        elif meta.objetivo == Objetivo.MANTER:
            return cls.avaliar_manutencao(registro, meta)

        return {"objetivo": "GERAL", "mensagem": "Registro salvo com sucesso!"}