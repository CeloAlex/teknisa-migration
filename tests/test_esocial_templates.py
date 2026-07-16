import asyncio

from httpx import AsyncClient

TIPO_S1030 = "MIG_ESOCIAL_S1030"
TIPO_S1200 = "MIG_ESOCIAL_S1200"
TIPO_S2230 = "MIG_ESOCIAL_S2230"
TIPO_S2200 = "MIG_ESOCIAL_S2200"
TIPO_S2205 = "MIG_ESOCIAL_S2205"
TIPO_S2206 = "MIG_ESOCIAL_S2206"


def _xml_s1030(cod_cargo: str = "123") -> bytes:
    return f"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtTabCargo/v_S_01_00_00">
      <evtTabCargo>
        <infoCargo>
          <inclusao>
            <ideCargo>
              <codCargo>{cod_cargo}</codCargo>
              <iniValid>2026-01</iniValid>
            </ideCargo>
            <dadosCargo>
              <nmCargo>Analista</nmCargo>
              <codCBO>252105</codCBO>
            </dadosCargo>
          </inclusao>
        </infoCargo>
      </evtTabCargo>
    </eSocial>""".encode("utf-8")


def _xml_s1200() -> bytes:
    return b"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00">
      <evtRemun>
        <ideEvento><perApur>2026-06</perApur></ideEvento>
        <dmDev>
          <infoPerApur>
            <ideEstabLot>
              <remunPerApur>
                <matricula>555</matricula>
                <itensRemun><codRubr>10</codRubr><vrRubr>100.50</vrRubr></itensRemun>
                <itensRemun><codRubr>43</codRubr><vrRubr>25.00</vrRubr></itensRemun>
              </remunPerApur>
            </ideEstabLot>
          </infoPerApur>
        </dmDev>
      </evtRemun>
    </eSocial>"""


def _xml_s2200(matricula: str = "20248", cnpj_legal: str = "01798914000960") -> bytes:
    return f"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtAdmissao/v_S_01_03_00">
      <evtAdmissao>
        <trabalhador>
          <cpfTrab>18306702719</cpfTrab>
          <nmTrab>ADRIAN GALDINO DUARTE</nmTrab>
          <sexo>M</sexo>
          <racaCor>3</racaCor>
          <estCiv>2</estCiv>
          <grauInstr>05</grauInstr>
          <nascimento>
            <dtNascto>2000-11-26</dtNascto>
            <paisNascto>105</paisNascto>
            <paisNac>105</paisNac>
          </nascimento>
          <endereco>
            <brasil>
              <tpLograd>R</tpLograd>
              <dscLograd>ENGENHEIRO WALCRUEZE MEIRELLES</dscLograd>
              <nrLograd>461</nrLograd>
              <bairro>PURYS</bairro>
              <cep>25808100</cep>
              <codMunic>3306008</codMunic>
              <uf>RJ</uf>
            </brasil>
          </endereco>
          <contato>
            <fonePrinc>24981649563</fonePrinc>
            <emailPrinc>galdinoadrian752@gmail.com</emailPrinc>
          </contato>
        </trabalhador>
        <vinculo>
          <matricula>{matricula}</matricula>
          <infoRegimeTrab>
            <infoCeletista>
              <dtAdm>2026-01-05</dtAdm>
              <tpAdmissao>1</tpAdmissao>
              <natAtividade>1</natAtividade>
              <cnpjSindCategProf>32316366000160</cnpjSindCategProf>
            </infoCeletista>
          </infoRegimeTrab>
          <infoContrato>
            <CBOCargo>513205</CBOCargo>
            <remuneracao><vrSalFx>2156</vrSalFx><undSalFixo>5</undSalFixo></remuneracao>
            <duracao><dtTerm>2026-02-18</dtTerm></duracao>
            <localTrabalho><localTrabGeral><nrInsc>{cnpj_legal}</nrInsc></localTrabGeral></localTrabalho>
          </infoContrato>
        </vinculo>
      </evtAdmissao>
    </eSocial>""".encode("utf-8")


def _xml_s2205(cpf: str = "00868199508") -> bytes:
    return f"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtAltCadastral/v_S_01_02_00">
      <evtAltCadastral>
        <ideTrabalhador><cpfTrab>{cpf}</cpfTrab></ideTrabalhador>
        <alteracao>
          <dtAlteracao>2024-01-01</dtAlteracao>
          <dadosTrabalhador>
            <nmTrab>ABEL RIBEIRO DOS SANTOS</nmTrab>
            <sexo>M</sexo>
            <racaCor>1</racaCor>
            <estCiv>1</estCiv>
            <grauInstr>05</grauInstr>
            <paisNac>105</paisNac>
            <endereco>
              <brasil>
                <tpLograd>R</tpLograd>
                <dscLograd>JOSE MARTINHO</dscLograd>
                <nrLograd>85</nrLograd>
                <bairro>PARQUE IMPERIAL</bairro>
                <cep>06462230</cep>
                <codMunic>3505708</codMunic>
                <uf>SP</uf>
              </brasil>
            </endereco>
            <contato>
              <fonePrinc>11962805148</fonePrinc>
              <emailPrinc>abelribeiro2619@gmail.com</emailPrinc>
            </contato>
          </dadosTrabalhador>
        </alteracao>
      </evtAltCadastral>
    </eSocial>""".encode("utf-8")


def _xml_s2206(matricula: str = "20248") -> bytes:
    return f"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtAltContratual/v_S_01_03_00">
      <evtAltContratual>
        <ideVinculo>
          <cpfTrab>18306702719</cpfTrab>
          <matricula>{matricula}</matricula>
        </ideVinculo>
        <altContratual>
          <dtAlteracao>2026-01-05</dtAlteracao>
          <vinculo>
            <infoRegimeTrab>
              <infoCeletista><cnpjSindCategProf>32316366000160</cnpjSindCategProf></infoCeletista>
            </infoRegimeTrab>
            <infoContrato>
              <CBOCargo>513205</CBOCargo>
              <duracao><dtTerm>2026-02-18</dtTerm></duracao>
              <localTrabalho><localTrabGeral><nrInsc>01798914000960</nrInsc></localTrabGeral></localTrabalho>
            </infoContrato>
          </vinculo>
        </altContratual>
      </evtAltContratual>
    </eSocial>""".encode("utf-8")


def _xml_s2230_ferias() -> bytes:
    return b"""<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtAfastTemp/v_S_01_03_00">
      <evtAfastTemp>
        <ideVinculo><matricula>777</matricula></ideVinculo>
        <infoAfastamento>
          <iniAfastamento>
            <dtIniAfast>2026-02-01</dtIniAfast>
            <codMotAfast>15</codMotAfast>
            <perAquis><dtInicio>2025-01-01</dtInicio><dtFim>2025-12-31</dtFim></perAquis>
          </iniAfastamento>
          <fimAfastamento><dtTermAfast>2026-03-01</dtTermAfast></fimAfastamento>
        </infoAfastamento>
      </evtAfastTemp>
    </eSocial>"""


async def _criar_migracao(client: AsyncClient, nr_org: int, tipo_codigo: str) -> dict:
    response = await client.post(
        "/migracoes", json={"nr_org": nr_org, "tipo_migracao_codigo": tipo_codigo, "operador": "Operador Teste"}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _upload_e_aguardar(
    client: AsyncClient, migracao_id: int, template_codigo: str, conteudo: bytes, filename: str
) -> dict:
    upload = await client.post(
        f"/migracoes/{migracao_id}/templates/{template_codigo}/arquivo",
        files={"arquivo": (filename, conteudo, "application/xml")},
        data={"usuario": "Operador Teste"},
    )
    assert upload.status_code == 202, upload.text
    for _ in range(100):
        resposta = (await client.get(f"/migracoes/{migracao_id}/templates/{template_codigo}")).json()
        if resposta["status"] in {"validado", "com_inconsistencias"}:
            return resposta
        await asyncio.sleep(0.02)
    raise AssertionError("Processamento não concluiu a tempo")


async def test_esocial_s1030_fluxo_completo_ate_script(client: AsyncClient, nr_org_teste: int) -> None:
    """Caso simples: XML de registro único, sem linhas repetidas."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S1030)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S1030", _xml_s1030(), "s1030.xml")
    assert status["status"] == "validado"
    assert status["total_linhas"] == 1

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S1030/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 200

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S1030/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200

    script = await client.get(f"/migracoes/{migracao_id}/templates/ESOCIAL_S1030/script")
    assert script.status_code == 200
    assert "GPE_OCUPACAOM" in script.text
    assert "GPE_OCUPACAOH" in script.text


async def test_esocial_s1200_gera_uma_linha_por_rubrica(client: AsyncClient, nr_org_teste: int) -> None:
    """Caso de nós repetidos: um evento de remuneração com 2 itens de rubrica vira 2 linhas."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S1200)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S1200", _xml_s1200(), "s1200.xml")
    assert status["status"] == "validado"
    assert status["total_linhas"] == 2


async def test_esocial_s2230_roteia_para_ferias_quando_codmotafast_15(client: AsyncClient, nr_org_teste: int) -> None:
    """Caso de roteamento condicional: codMotAfast=15 deve gerar o bloco de Férias."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S2230)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S2230", _xml_s2230_ferias(), "s2230.xml")
    assert status["status"] in {"validado", "com_inconsistencias"}

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2230/aprovar-dados", json={"usuario": "Carlos"}
    )
    if aprovar.status_code != 200:
        # NRSITUFUNCM é obrigatório e não tem origem no XML (gap documentado) — se a
        # validação clássica bloquear por outro motivo, falha o teste explicitamente.
        raise AssertionError(f"Aprovação de dados falhou inesperadamente: {aprovar.text}")

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2230/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200

    script = await client.get(f"/migracoes/{migracao_id}/templates/ESOCIAL_S2230/script")
    assert script.status_code == 200
    assert "FPA_FERIAS" in script.text
    assert "FPA_GOZOFERIAS" in script.text
    assert "GPE_ALTESITUFUNC" not in script.text


async def test_esocial_s2200_admissao_fluxo_completo_ate_script(client: AsyncClient, nr_org_teste: int) -> None:
    """S-2200 (Admissão) reaproveita a forma dos blocos de INSERT do template VINCULO
    completo (revision 1d7a77f2492c) — confere que os blocos sempre gerados aparecem e que
    o e-mail (contato/emailPrinc) chega ao script."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S2200)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S2200", _xml_s2200(), "s2200.xml")
    assert status["status"] in {"validado", "com_inconsistencias"}
    assert status["total_linhas"] == 1

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2200/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 200, aprovar.text

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2200/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200, gerar.text

    script = await client.get(f"/migracoes/{migracao_id}/templates/ESOCIAL_S2200/script")
    assert script.status_code == 200
    sql = script.text
    assert "INSERT INTO PARCNEGOCIO (" in sql
    assert "INSERT INTO GPE_PESSOAH (" in sql
    assert "INSERT INTO GPE_VINCULOM (" in sql
    assert "INSERT INTO GPE_VINCULOH (" in sql
    assert "INSERT INTO GPE_ALTESITUFUNC (" in sql
    assert "galdinoadrian752@gmail.com" in sql
    assert "INSERT INTO ENDERECOPARC (" in sql
    assert "PURYS" in sql


async def test_esocial_s2205_altera_dados_cadastrais(client: AsyncClient, nr_org_teste: int) -> None:
    """S-2205 (Alteração de Dados Cadastrais) sempre insere um novo histórico de pessoa
    (simplificação documentada na migração e54519c6e6b6, em vez da lógica condicional
    update-em-vaco-ou-insere-histórico do PHP de referência)."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S2205)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S2205", _xml_s2205(), "s2205.xml")
    assert status["status"] in {"validado", "com_inconsistencias"}

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2205/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 200, aprovar.text

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2205/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200, gerar.text

    script = await client.get(f"/migracoes/{migracao_id}/templates/ESOCIAL_S2205/script")
    assert script.status_code == 200
    sql = script.text
    assert "INSERT INTO GPE_PESSOAH (" in sql
    assert "ABEL RIBEIRO DOS SANTOS" in sql
    assert "abelribeiro2619@gmail.com" in sql


async def test_esocial_s2206_altera_contrato_trabalho(client: AsyncClient, nr_org_teste: int) -> None:
    """S-2206 (Alteração de Contrato de Trabalho) resolve NRVINCULOM por matrícula (subquery,
    mesmo padrão do UPDATE em GPE_VINCULOM do S-2299) e só grava movimentação legal."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_S2206)
    migracao_id = migracao["id"]

    status = await _upload_e_aguardar(client, migracao_id, "ESOCIAL_S2206", _xml_s2206(), "s2206.xml")
    assert status["status"] in {"validado", "com_inconsistencias"}

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2206/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 200, aprovar.text

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/ESOCIAL_S2206/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200, gerar.text

    script = await client.get(f"/migracoes/{migracao_id}/templates/ESOCIAL_S2206/script")
    assert script.status_code == 200
    sql = script.text
    assert "INSERT INTO GPE_VINCULOH (" in sql
    assert "CDMATRICULA = '20248'" in sql
    assert "INSERT INTO GPE_MOVIMENTACAO (" in sql
