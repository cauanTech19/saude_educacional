def test_rota_register_sucesso(client, dados_usuario_validos):
    response = client.post("/api/auth/register", json=dados_usuario_validos)
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["mensagem"] == "Usuário cadastrado com sucesso!"
    assert "usuario" in json_data


def test_rota_register_erro_pydantic_payload_invalido(client, dados_usuario_validos):
    dados = dados_usuario_validos.copy()
    dados["email"] = "email_invalido"  # Força erro do Pydantic

    response = client.post("/api/auth/register", json=dados)
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert "erro" in json_data


def test_rota_login_sucesso(client, dados_usuario_validos):
    # Cadastra o usuário primeiro
    client.post('/api/auth/register', json=dados_usuario_validos)

    # Faz o login via cliente HTTP do Flask
    response = client.post('/api/auth/login', json={
        'email': dados_usuario_validos['email'],
        'senha': dados_usuario_validos['senha']
    })

    json_data = response.get_json()
    assert response.status_code == 200
    assert 'access_token' in json_data


def test_rota_login_credenciais_invalidas(client, usuario_db, dados_usuario_validos):
    payload = {
        "email": dados_usuario_validos["email"],
        "senha": "senha_totalmente_errada"
    }
    
    response = client.post("/api/auth/login", json=payload)
    
    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data["mensagem"] == "E-mail ou senha estão incorretos."


def test_atualizar_perfil_sucesso(client, usuario_db, dados_usuario_validos):
    # 1. Faz login para obter o token
    login_res = client.post("/api/auth/login", json={
        "email": dados_usuario_validos["email"],
        "senha": dados_usuario_validos["senha"]
    })
    token = login_res.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch_res = client.put("/api/auth/atualizar", json={
        "nome": "Carlos Eduardo Silva"    }, headers=headers)

    assert patch_res.status_code == 200
    assert patch_res.get_json()["usuario"]["nome"] == "Carlos Eduardo Silva"


def test_logout_revoga_token(client, usuario_db, dados_usuario_validos):
    # 1. Faz login
    login_res = client.post("/api/auth/login", json={
        "email": dados_usuario_validos["email"],
        "senha": dados_usuario_validos["senha"]
    })
    token = login_res.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Executa o Logout
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 3. Tenta usar o MESMO token após o logout (deve ser negado 401)
    tentativa_res = client.put("/api/auth/atualizar", json={"nome": "Teste"}, headers=headers)
    assert tentativa_res.status_code == 401



def test_desativar_conta_com_sucesso(client, dados_usuario_validos):
    # 1. Cadastra o usuário
    res_reg = client.post("/api/auth/register", json=dados_usuario_validos)
    assert res_reg.status_code == 201

    # 2. Faz login para obter o token
    payload_login = {
        "email": dados_usuario_validos["email"],
        "senha": dados_usuario_validos["senha"]
    }
    res_login = client.post("/api/auth/login", json=payload_login)
    token = res_login.get_json()["access_token"]

    # 3. Chama a rota de desativação enviando o Token
    headers = {"Authorization": f"Bearer {token}"}
    res_delete = client.delete("/api/auth/desativar", headers=headers)

    assert res_delete.status_code == 200
    assert res_delete.get_json()["mensagem"] == "Conta desativada com sucesso."

    # 4. Tenta fazer login novamente e deve falhar porque a conta está inativa
    res_login_novo = client.post("/api/auth/login", json=payload_login)
    assert res_login_novo.status_code == 200
    assert 'access_token' in res_login_novo.get_json()



def test_obter_perfil_com_sucesso(client, dados_usuario_validos):
  # 1. Cadastra o usuário
  client.post('/api/auth/register', json=dados_usuario_validos)

  # 2. Faz login para obter o token
  payload_login = {
    'email': dados_usuario_validos['email'],
    'senha': dados_usuario_validos['senha'],
  }
  
  res_login = client.post('/api/auth/login', json=payload_login)
  token = res_login.get_json()['access_token']

  # 3. Busca o perfil
  headers = {'Authorization': f'Bearer {token}'}
  response = client.get('/api/auth/info', headers=headers)
  json_data = response.get_json()

  assert response.status_code == 200
  assert json_data['email'] == dados_usuario_validos['email']
  assert json_data['nome'] == dados_usuario_validos['nome']
  assert 'senha_hash' not in json_data  