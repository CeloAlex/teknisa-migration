<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\Repositories;
use HCM\Util\DateUtil;

class ImportacaoXmlS2240 extends ImportacaoXmlEvento
{
  const NMEVENTO = "S-2240";

  public function importarXml()
  {
    $evtExpRisco = (array) $this->xml->evtExpRisco;
    if ($evtExpRisco) {
      $parameters = [
        "NRORG" => $this->nrorg,
        "CDOPERADOR" => $this->cdoperador,
        "DTMESCOMPETENC" => $this->dtcompetencia,
        "EVTEXPRISCO" => $evtExpRisco,
      ];

      $s2240 = new S2240($this->entityManager, $parameters);

      return $s2240->importacao();
    }

    return [
      "status" => false,
      "message" =>
        self::MSG_ERRO_XML . " (Ausência da tag 'evtExpRisco' no arquivo).",
    ];
  }
  

}

class S2240
{
  protected $entityManager, $parameters, $repository;

  public function __construct($entityManager, $parameters)
  {
    $this->entityManager = $entityManager;
    $this->parameters = $parameters;
    $this->fatorRiscoPorVinculo = new FatorRiscoPorVinculo($this->entityManager, $this->parameters);
    $this->setDsobservacao      = new SetDsobservacao($this->entityManager, $this->parameters);
  }

  public function importacao()
  {
    if ($this->fatorRiscoPorVinculo->vinculoNotExists()){
      return ["status" => false, "message" => "Vínculo não encontrado"];
    }

    if ($this->fatorRiscoPorVinculo->alreadyExistsFatorRiscoPorVinculo()) {
      return ["status" => false, "message" => 'Fator de Risco Por Vínculo já existe.'];
    }
    
    $this->fatorRiscoPorVinculo->inserir();
    
   $this->setDsobservacao->findDsobservacao();

    return ["status" => true, "messages" => []];
  }
    
}

class SetDsobservacao extends Parametros
  {
    
    protected $entityManager;
    protected $parameter;

    public function __construct($entityManager, $parameters)
    {
      $this->entityManager = $entityManager;
      $this->parameters = $parameters;
    }
    
    public function findDsobservacao()
    
    {
      $nrorg             = $this->operador()["NRORG"];
      $dtmescompetenc    = $this->operador()["DTMESCOMPETENC"];
      $nrvinculom        = $this->nrVinculom();
      $objAlteocupacao   = $this->retornaObjAlteocupacao($nrvinculom,$nrorg,$dtmescompetenc);
      $dsObservacao      = $this->infoAtiv()["dscAtivDes"];
      if(substr($dsObservacao, 0, 2) == '{{'){
        return;
      }else{ 
        $this->updateGpe_Alteocupacao($objAlteocupacao,$dsObservacao,$nrorg);
      }
    }
    
    public function retornaObjAlteocupacao($nrvinvulom,$nrorg,$dtmescompetenc)
    {
      $objAlteocupacao = $this->entityManager->getRepository(Repositories::GPE_ALTEOCUPACAO)->retornaUltimaAlteracaoOcupacaoVinculo($nrorg, $dtmescompetenc, $nrvinvulom);
      if($objAlteocupacao){
        return $objAlteocupacao;
      }else{
        return;
      }
    }
    
    public function updateGpe_Alteocupacao($objAlteocupacao,$dsObservacao,$nrorg)
    {
      $cdoperador = $this->operador()["CDOPERADOR"];
      try {
        $objAlteocupacao->setDsobservacao($dsObservacao);
        $objAlteocupacao->setCdoperultatu ($cdoperador);
        $objAlteocupacao->setNrorgultatu ($nrorg);
        $objAlteocupacao->setDtultatu (DateUtil::getDataAtual());
        $this->entityManager->persist($objAlteocupacao);               
        $this->entityManager->flush();
      } catch (\Exception $e) {
        throw $e;
      }
    }
  }

class FatorRiscoPorVinculo
{
  protected $entityManager;
  protected $parameters;
  protected $repositoryFatorRisco;

  public function __construct($entityManager, $parameters)
  {
    $this->entityManager = $entityManager;
    $this->parameters = $parameters;

    $this->repositoryFatorRisco = new RepositoryFatorRisco(
      $this->entityManager,
      $this->parameters
    );
  }

  public function inserir()
  {

    if (!$this->repositoryFatorRisco->alreadyExistsFatorRisco()) {
      $this->repositoryFatorRisco->insertFatorRisco();
    }

    $this->repositoryFatorRisco->insertFatorRiscoPorVinculo();
  }

  public function alreadyExistsFatorRiscoPorVinculo()
  {
    return $this->repositoryFatorRisco->alreadyExistsFatorRiscoPorVinculo();
  }

  public function vinculoNotExists()
  {
    return $this->repositoryFatorRisco->vinculoNotExists();
  }

}

class RepositoryFatorRisco extends Parametros
{
  public function alreadyExistsFatorRisco()
  {
    $fatorRisco = $this->getFatorRisco();

    if (empty($fatorRisco)) {
      return false;
    }

    return true;
  }

  private function getFatorRisco(): array
  {
    $fatorRisco = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SELECT_SST_FATORRISCO);

    $fatorRisco->execute([
      "NRORG" => $this->operador()["NRORG"],
      "NRAGENTENOCIVO" => $this->agenteNocivo()[0]["NRAGENTENOCIVO"],
    ]);

    return $fatorRisco->fetchAll();
  }

  public function alreadyExistsFatorRiscoPorVinculo()
  {
    $fatorRiscoPorVinculo = $this->getFatorRiscoPorVinculo();

    if (empty($fatorRiscoPorVinculo)) {
      return false;
    }

    return true;
  }

  private function getFatorRiscoPorVinculo()
  {
    $fatorRiscoPorVinculo = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SELECT_SST_RELVINCRISCO);
    if (!empty($this->getFatorRisco())) {
      $fatorRiscoPorVinculo->execute([
        "NRORG" => $this->operador()["NRORG"],
        "NRVINCULOM" => $this->nrVinculom(),
        "NRFATORRISCO" => $this->getFatorRisco()[0]["NRFATORRISCO"],
      ]);

      return $fatorRiscoPorVinculo->fetchAll();
    }

    return [];
  }

  public function insertFatorRiscoPorVinculo()
  {
    $fatorRiscoPorVinculo = $this->entityManager
      ->getConnection()
      ->prepare(Queries::INSERT_SST_RELVINCRISCO);

    $fatorRiscoPorVinculo->execute([
      "NRORG" => $this->operador()["NRORG"],
      "NRFATORRISCO" => $this->getFatorRisco()[0]["NRFATORRISCO"],
      "NRVINCULOM" => $this->nrVinculom(),
      "DTINIVIGENCIA" => $this->infoExpRisco()["dtIniCondicao"],
      "DTFIMVIGENCIA" => null,
      "CDOPERINCLUSAO" => $this->operador()["CDOPERADOR"],
    ]);
  }

  public function insertFatorRisco()
  {
    $fatorRisco = $this->entityManager
      ->getConnection()
      ->prepare(Queries::INSERT_SST_FATORRISCO);

    $fatorRisco->execute([
      "NRORG" => $this->operador()["NRORG"],
      "NMFATORRISCO" => substr($this->agenteNocivo()[0]["DSAGENTENOCIVO"], 0, 100),
      "DSFATORRISCO" => $this->agenteNocivo()[0]["DSAGENTENOCIVO"],
      "IDFATORRISCO" => 'F',
      "DTINIVIGENCIA" => $this->infoExpRisco()["dtIniCondicao"],
      "DTFIMVIGENCIA" => null,
      "CDOPERINCLUSAO" => $this->operador()["CDOPERADOR"],
      "NRAGENTENOCIVO" => $this->agenteNocivo()[0]["NRAGENTENOCIVO"],
    ]);
  }

  public function vinculoNotExists()
  {
    if ($this->nrVinculom() == null) {
      return true;
    }

    return false;
  }
}

class Parametros
{
  public function __construct($entityManager, $parameters)
  {
    $this->entityManager = $entityManager;
    $this->parameters = $parameters;
  }

  public function operador(): array
  {
    return [
      "CDOPERADOR" => $this->parameters["CDOPERADOR"],
      "NRORG" => $this->parameters["NRORG"],
      "DTMESCOMPETENC" => $this->parameters["DTMESCOMPETENC"],
    ];
  }

  public function ideEvento(): array
  {
    $ideEvento = (array) $this->parameters["EVTEXPRISCO"]["ideEvento"];

    return [
      "ideEvento" => $ideEvento,
      "indRetif" => $ideEvento["indRetif"],
      "nrRecibo" => isset($ideEvento["nrRecibo"])
        ? $ideEvento["nrRecibo"]
        : null,
      "tpAmb" => $ideEvento["tpAmb"],
      "procEmi" => $ideEvento["procEmi"],
      "verProc" => $ideEvento["verProc"],
    ];
  }

  public function ideEmpregador(): array
  {
    $ideEmpregador = (array) $this->parameters["EVTEXPRISCO"]["ideEmpregador"];

    return [
      "ideEmpregador" => $ideEmpregador,
      "tpInsc" => $ideEmpregador["tpInsc"],
      "nrInsc" => $ideEmpregador["nrInsc"],
    ];
  }

  public function ideVinculo(): array
  {
    $ideVinculo = (array) $this->parameters["EVTEXPRISCO"]["ideVinculo"];

    return [
      "ideVinculo" => $ideVinculo,
      "cpfTrab" => $ideVinculo["cpfTrab"],
      "matricula" => isset($ideVinculo["matricula"])
        ? $ideVinculo["matricula"]
        : null,
      "codCateg" => isset($ideVinculo["codCateg"])
        ? $ideVinculo["codCateg"]
        : null,
    ];
  }

  public function infoExpRisco(): array
  {
    $infoExpRisco = (array) $this->parameters["EVTEXPRISCO"]["infoExpRisco"];

    $infoExpRisco["dtIniCondicao"] = strtotime($infoExpRisco["dtIniCondicao"]);
    $infoExpRisco["dtIniCondicao"] = date(
      "Y/m/d",
      $infoExpRisco["dtIniCondicao"]
    );
    $infoExpRisco["dtIniCondicao"] = \DateTime::createFromFormat(
      "Y/m/d",
      $infoExpRisco["dtIniCondicao"]
    )->format("d/m/Y");

    return [
      "infoExpRisco" => $infoExpRisco,
      "dtIniCondicao" => $infoExpRisco["dtIniCondicao"],
    ];
  }

  public function infoAmb(): array
  {
    $infoAmb = (array) $this->infoExpRisco()["infoExpRisco"]["infoAmb"];

    return [
      "infoAmb" => $infoAmb,
      "localAmb" => $infoAmb["localAmb"],
      "dscSetor" => $infoAmb["dscSetor"],
      "tpInsc" => $infoAmb["tpInsc"],
      "nrInsc" => $infoAmb["nrInsc"],
    ];
  }

  public function infoAtiv(): array
  {
    $infoAtiv = (array) $this->infoExpRisco()["infoExpRisco"]["infoAtiv"];

    return [
      "infoAtiv" => $infoAtiv,
      "dscAtivDes" => $infoAtiv["dscAtivDes"],
    ];
  }

  public function agNoc(): array
  {
    $agNoc = (array) $this->infoExpRisco()["infoExpRisco"]["agNoc"];

    return [
      "agNoc" => $agNoc,
      "codAgNoc" => $agNoc["codAgNoc"],
      "dscAgNoc" => isset($agNoc["dscAgNoc"]) ? $agNoc["dscAgNoc"] : null,
      "tpAval" => isset($agNoc["tpAval"]) ? $agNoc["tpAval"] : null,
      "intConc" => isset($agNoc["intConc"]) ? $agNoc["intConc"] : null,
      "limTol" => isset($agNoc["limTol"]) ? $agNoc["limTol"] : null,
      "unMed" => isset($agNoc["unMed"]) ? $agNoc["unMed"] : null,
      "tecMedicao" => isset($agNoc["tecMedicao"]) ? $agNoc["tecMedicao"] : null,
    ];
  }

  public function epcEpi(): array
  {
    $epcEpi = (array) $this->agNoc()["agNoc"]["epcEpi"];

    return [
      "epcEpi" => $epcEpi,
      "utilizEPC" => $epcEpi["utilizEPC"],
      "eficEpc" => isset($epcEpi["eficEPC"]) ? $epcEpi["eficEPC"] : null,
      "utilizEPI" => $epcEpi["utilizEPI"],
      "eficEpi" => isset($epcEpi["eficEPI"]) ? $epcEpi["eficEPI"] : null,
    ];
  }

  public function epi(): array
  {
    $epi = (array) $this->epcEpi()["epcEpi"]["epi"];

    return [
      "epi" => $epi,
      "docAval" => isset($epi["docAval"]) ? $epi["docAval"] : null,
      "dscEPI" => isset($epi["dscEPI"]) ? $epi["dscEPI"] : null,
    ];
  }

  public function epiCompl(): array
  {
    $epiCompl = (array) $this->epcEpi()["epcEpi"]["epiCompl"];

    return [
      "epiCompl" => $epiCompl,
      "medProtecao" => $epiCompl["medProtecao"],
      "condFuncto" => $epiCompl["condFuncto"],
      "usoInint" => $epiCompl["usoInint"],
      "przValid" => $epiCompl["przValid"],
      "periodicTroca" => $epiCompl["periodicTroca"],
      "higienizacao" => $epiCompl["higienizacao"],
    ];
  }

  public function respReg(): array
  {
    $respReg = (array) $this->infoExpRisco()["infoExpRisco"]["respReg"];

    return [
      "respReg" => $respReg,
      "cpfResp" => $respReg["cpfResp"],
      "ideOC" => $respReg["ideOC"],
      "dscOC" => isset($respReg["dscOC"]) ? $respReg["dscOC"] : null,
      "nrOC" => $respReg["nrOC"],
      "ufOC" => $respReg["ufOC"],
    ];
  }

  public function obs(): array
  {
    $obs = (array) $this->infoExpRisco()["infoExpRisco"]["obs"];

    return [
      "obs" => $obs,
      "obsCompl" => $obs["obsCompl"],
    ];
  }
  
  public function agenteNocivo(): array
  {
    $agenteNocivo = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SELECT_NRAGENTENOCIVO_ESO_AGENTENOCIVO);

    $agenteNocivo->execute([
      "CDAGNOC" => $this->agNoc()["codAgNoc"],
    ]);

    return $agenteNocivo->fetchAll();
  }

  public function nrVinculom()
  {
    $vinculo = $this->entityManager
      ->getRepository(Repositories::GPE_VINCULOM)
      ->retornaVinculoPorCPF(
        $this->operador()["NRORG"],
        $this->ideVinculo()["cpfTrab"],
        $this->ideVinculo()["matricula"],
        $this->operador()["DTMESCOMPETENC"],
        $this->ideVinculo()["codCateg"],
        "S"
      );

    return isset($vinculo[0]) ? $vinculo[0]->getNrvinculom() : null;
  }
}

class Queries
{
  const SELECT_NRAGENTENOCIVO_ESO_AGENTENOCIVO = "
    SELECT * FROM ESO_AGENTENOCIVO WHERE CDESOCIAL = :CDAGNOC
  ";

  const SELECT_SST_FATORRISCO = "
    SELECT * FROM SST_FATORRISCO WHERE NRORG = :NRORG AND NRAGENTENOCIVO = :NRAGENTENOCIVO
  ";

  const SELECT_SST_RELVINCRISCO = "
    SELECT * 
      FROM SST_RELVINCRISCO 
     WHERE NRORG = :NRORG AND NRVINCULOM = :NRVINCULOM AND NRFATORRISCO = :NRFATORRISCO
  ";
  

  const INSERT_SST_RELVINCRISCO = "
    INSERT INTO SST_RELVINCRISCO (
      NRORG,
      NRRELVINCFATRISCO,
      NRFATORRISCO,
      NRVINCULOM,
      DTINIVIGENCIA,
      DTFIMVIGENCIA,
      IDATIVO,
      NRORGINCLUSAO,
      DTINCLUSAO,
      CDOPERINCLUSAO
    ) 
    VALUES (
      :NRORG,
      (SELECT NVL(MAX(NRRELVINCFATRISCO), 0) + 1 FROM SST_RELVINCRISCO WHERE NRORG = :NRORG),
      :NRFATORRISCO,
      :NRVINCULOM,
      :DTINIVIGENCIA,
      :DTFIMVIGENCIA,
      'S',
      :NRORG,
      SYSDATE,
      :CDOPERINCLUSAO
    )
  ";

  const INSERT_SST_FATORRISCO = "
    INSERT INTO SST_FATORRISCO (
      NRORG,
      NRFATORRISCO,
      NMFATORRISCO,
      DSFATORRISCO,
      IDFATORRISCO,
      DTINIVIGENCIA,
      DTFIMVIGENCIA,
      DSINTENSIDADE,
      DSTECNICA,
      IDEPCEFICAZ,
      IDEPIEFICAZ,
      IDATIVO,
      NRORGINCLUSAO,
      DTINCLUSAO,
      CDOPERINCLUSAO,
      IDGERAINSAL,
      IDGERAPERIC,
      IDGERAAPOSESPEC,
      NRAGENTENOCIVO
    ) 
    VALUES (
      :NRORG,
      (SELECT NVL(MAX(NRFATORRISCO), 0) + 1 FROM SST_FATORRISCO WHERE NRORG = :NRORG),
      :NMFATORRISCO,
      :DSFATORRISCO,
      :IDFATORRISCO,
      :DTINIVIGENCIA,
      :DTFIMVIGENCIA,
      'N/A',
      'N/A',
      'N',
      'N',
      'S',
      :NRORG,
      SYSDATE,
      :CDOPERINCLUSAO,
      'N',
      'N',
      'S',
      :NRAGENTENOCIVO
    )
  ";

}
