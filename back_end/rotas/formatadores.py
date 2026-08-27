from pydantic import ValidationError

def formatar_erros_pydantic(e: ValidationError) -> list[str]:
  mensagens = []
  
  TRADUCOES = {
      'string_type': 'O campo deve ser um texto.',
      'missing': 'Este campo é obrigatório.',
      'enum': 'Opção inválida selecionada.',
      'string_too_short': 'O campo não pode estar vazio.',
      'none_required': 'Este campo não pode ser nulo.',
      'none_is_not_allowed': 'Este campo não pode ser nulo.',
      'type_error.none.not_allowed': 'Este campo não pode ser nulo.',
      # --- TRADUÇÕES DE TIPO NUMÉRICO ---
      'float_type': 'Este campo não pode ser nulo.',
      'int_type': 'Este campo não pode ser nulo.',
      'number_type': 'Este campo não pode ser nulo.',
  }

  for erro in e.errors():
    campo = erro['loc'][0] if erro['loc'] else 'geral'
    tipo_erro = erro['type']
    msg_original = erro['msg']
    ctx = erro.get('ctx', {})

    # 1. Trata erro específico de Email
    if 'email' in tipo_erro or 'valid email address' in msg_original:
      msg = 'Informe um e-mail válido (ex: nome@dominio.com).'

    # Trata especificamente o bloqueio do extra='forbid'
    elif tipo_erro == 'extra_forbidden':
      msg = f"O campo '{campo}' não é permitido nesta requisição."

    # 2. Trata se foi passado None para campo float/int/number ou mensagem "Input should be a valid..."
    elif (
        'float' in tipo_erro
        or 'int' in tipo_erro
        or 'number' in tipo_erro
        or 'input should be a valid' in msg_original.lower()
    ):
      msg = 'Este campo não pode ser nulo.'

    # 3. Trata limites MÍNIMOS (gt / ge)
    elif tipo_erro in ('greater_than', 'greater_than_equal'):
        limite = (
            ctx.get('gt') if ctx.get('gt') is not None else ctx.get('ge')
        )
        msg = f'O valor deve ser maior que {limite}.'

    # 4. Trata limites MÁXIMOS (lt / le)
    elif tipo_erro in ('less_than', 'less_than_equal'):
        limite = (
            ctx.get('lt') if ctx.get('lt') is not None else ctx.get('le')
        )
        msg = f'O valor deve ser menor que {limite}.'
        
    # 5. Remove o prefixo "Value error, "
    elif msg_original.startswith('Value error, '):
      msg = msg_original.replace('Value error, ', '')

    # 6. Trata nulo genérico
    elif 'none' in tipo_erro.lower():
      msg = 'Este campo não pode ser nulo.'

    else:
      msg = TRADUCOES.get(tipo_erro, msg_original)

    mensagens.append(f'{campo}: {msg}')

  return mensagens