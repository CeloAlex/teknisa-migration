from app.metadata.ddl_import import parse_ddl_oracle

DDL_EXEMPLO = """
--------------------------------------------------------
--  DDL for Table GPE_TURNO
--------------------------------------------------------

  CREATE TABLE "FOLHA"."GPE_TURNO"
   (	"NRORG" NUMBER DEFAULT 1,
	"NRTURNO" NUMBER,
	"NRESCALATRABM" NUMBER,
	"DTDATABASE" DATE,
	"IDATIVO" VARCHAR2(1 BYTE) DEFAULT 'S',
	"DSTURNO" VARCHAR2(100 BYTE)
   ) SEGMENT CREATION IMMEDIATE
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255
  TABLESPACE "FOLHA" ;
--------------------------------------------------------
--  DDL for Index GPE_TURNO_1
--------------------------------------------------------

  CREATE INDEX "FOLHA"."GPE_TURNO_1" ON "FOLHA"."GPE_TURNO" ("NRTURNO", "NRORG", "DTDATABASE")
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS
  TABLESPACE "FOLHA" ;
--------------------------------------------------------
--  Constraints for Table GPE_TURNO
--------------------------------------------------------

  ALTER TABLE "FOLHA"."GPE_TURNO" ADD CONSTRAINT "CKC_IDATIVO_GPE_TURNO" CHECK (
            IDATIVO is null or (IDATIVO in ('S','N'))) ENABLE;
  ALTER TABLE "FOLHA"."GPE_TURNO" ADD CONSTRAINT "PK_GPE_TURNO" PRIMARY KEY ("NRORG", "NRTURNO")
  USING INDEX "FOLHA"."GPE_TURNO_1"  ENABLE;
  ALTER TABLE "FOLHA"."GPE_TURNO" MODIFY ("NRORG" NOT NULL ENABLE);
  ALTER TABLE "FOLHA"."GPE_TURNO" MODIFY ("NRTURNO" NOT NULL ENABLE);
  ALTER TABLE "FOLHA"."GPE_TURNO" MODIFY ("DSTURNO" NOT NULL ENABLE);
--------------------------------------------------------
--  DDL for Table GPE_ESCALATRABM
--------------------------------------------------------

  CREATE TABLE "FOLHA"."GPE_ESCALATRABM"
   (	"NRORG" NUMBER DEFAULT 1,
	"NRESCALATRABM" NUMBER,
	"NMESCALATRABH" VARCHAR2(60 BYTE)
   ) SEGMENT CREATION IMMEDIATE
  TABLESPACE "FOLHA" ;
  ALTER TABLE "FOLHA"."GPE_ESCALATRABM" MODIFY ("NRESCALATRABM" NOT NULL ENABLE);
"""


def test_parse_ddl_extrai_tabelas_e_colunas() -> None:
    tabelas = parse_ddl_oracle(DDL_EXEMPLO)
    nomes = {t.nome_tabela for t in tabelas}
    assert nomes == {"GPE_TURNO", "GPE_ESCALATRABM"}


def test_parse_ddl_ignora_indices_e_constraints() -> None:
    tabelas = {t.nome_tabela: t for t in parse_ddl_oracle(DDL_EXEMPLO)}
    turno = tabelas["GPE_TURNO"]
    colunas = {c.nome_coluna for c in turno.colunas}
    # 6 colunas reais do CREATE TABLE — nada vindo do CREATE INDEX/ADD CONSTRAINT.
    assert colunas == {"NRORG", "NRTURNO", "NRESCALATRABM", "DTDATABASE", "IDATIVO", "DSTURNO"}


def test_parse_ddl_marca_obrigatoriedade_via_modify_not_null() -> None:
    tabelas = {t.nome_tabela: t for t in parse_ddl_oracle(DDL_EXEMPLO)}
    por_nome = {c.nome_coluna: c for c in tabelas["GPE_TURNO"].colunas}
    assert por_nome["NRORG"].obrigatoria is True
    assert por_nome["NRTURNO"].obrigatoria is True
    assert por_nome["DSTURNO"].obrigatoria is True
    assert por_nome["DTDATABASE"].obrigatoria is False


def test_parse_ddl_extrai_tipo_dado() -> None:
    tabelas = {t.nome_tabela: t for t in parse_ddl_oracle(DDL_EXEMPLO)}
    por_nome = {c.nome_coluna: c for c in tabelas["GPE_TURNO"].colunas}
    assert por_nome["NRORG"].tipo_dado == "NUMBER"
    assert por_nome["IDATIVO"].tipo_dado == "VARCHAR2(1 BYTE)"
    assert por_nome["DSTURNO"].tipo_dado == "VARCHAR2(100 BYTE)"


def test_parse_ddl_multiplas_tabelas_no_mesmo_arquivo() -> None:
    tabelas = {t.nome_tabela: t for t in parse_ddl_oracle(DDL_EXEMPLO)}
    escala = tabelas["GPE_ESCALATRABM"]
    assert len(escala.colunas) == 3
    por_nome = {c.nome_coluna: c for c in escala.colunas}
    assert por_nome["NRESCALATRABM"].obrigatoria is True
    assert por_nome["NMESCALATRABH"].tipo_dado == "VARCHAR2(60 BYTE)"
