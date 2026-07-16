<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\Repositories;
use HCM\Util\DateUtil;

class ImportacaoXmlS2220 extends ImportacaoXmlEvento
{
  const NMEVENTO = "S-2220";

  public function __construct(
    $nrorg,
    $nrorgpadrao,
    $dtcompetencia,
    $cdoperador,
    $xml
  ) {
    parent::__construct(
      $nrorg,
      $nrorgpadrao,
      $dtcompetencia,
      $cdoperador,
      $xml
    );
  }

  public function importarXml()
  {
    $evtMonit = (array) $this->xml->evtMonit;

    if ($evtMonit) {
      $parameters = [
        "NRORG" => $this->nrorg,
        "CDOPERADOR" => $this->cdoperador,
        "DTMESCOMPETENC" => $this->dtcompetencia,
        "EVTMONIT" => $evtMonit,
      ];

      $s2220 = new S2220($this->entityManager, $parameters);

      if ($s2220->vinculoExists()) {
        if ($s2220->fichaMedicaExists()) {
          return ["status" => false, "message" => "Ficha Médica já existe"];
        }
        
        $s2220->importar();

        return ["status" => true, "messages" => []];
      }

      return ["status" => false, "message" => "Vínculo não encontrado"];
    }

    return [
      "status" => false,
      "message" =>
        self::MSG_ERRO_XML . " (Ausência da tag 'evtMonit' no arquivo).",
    ];
  }
}

class S2220
{
  protected $entityManager;
  protected $parameters;
  protected $repository;

  public function __construct($entityManager, $parameters)
  {
    $this->entityManager = $entityManager;
    $this->parameters = $parameters;

    $this->repository = new Repository($this->entityManager, $this->parameters);
  }

  public function importar()
  {
    try {
      $this->repository->setMedicoResponsavel();
      $this->repository->setFichaMedica();
      $this->repository->setTabResultExame();
      $this->repository->setExameFichaMed();

      $this->entityManager->flush();
    } catch (\Exception $e) {
      throw new \Exception($e->getMessage(), $e->getCode());
    }
  }

  public function vinculoExists()
  {
    return $this->repository->vinculoExists();
  }

  public function fichaMedicaExists()
  {
    return $this->repository->fichaMedicaExists();
  }
}

class Repository extends Parametros
{
  public function setFichaMedica()
  {
    $sql = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SST_FICHAMEDICA);

    $sql->execute([
      "NRVINCULOM" => $this->nrVinculom(),
      "NRPARCNEGOCIO" => $this->parcNegocio->getNrparcnegocio(),
      "DTHRPREVFICHAMED" => $this->aso()["dtAso"],
      "NRNATUREZAEXAME" => $this->naturezaexame->getNrnaturezaexame(),
      "NRORG" => $this->operador()["NRORG"],
      "CDOPERINCLUSAO" => $this->operador()["CDOPERADOR"],
    ]);
  }

  // TODO: Foreach
  public function setTabResultExame()
  {
    $this->tabResultExame = $this->entityManager->getRepository(Repositories::SST_TABRESULTEXAME)->findOneBy(array('nrorg' => $this->operador()["NRORG"], 'dstabresultexame' => substr($this->naturezaexame->getNmnaturezaexame(),0,50)));
    
    if(!$this->tabResultExame){
      $sql = $this->entityManager
        ->getConnection()
        ->prepare(Queries::SST_TABRESULTEXAME);
  
      $sql->execute([
        "NRORG" => $this->operador()["NRORG"],
        "DSTABRESULTEXAME" => substr($this->naturezaexame->getNmnaturezaexame(),0,50),
        "IDRESULTEXAME" => $this->exame()[0]["indResult"],
        "IDAPTO" => $this->aso()["resAso"],
        "CDOPERINCLUSAO" => $this->operador()["CDOPERADOR"],
      ]);
      
      $this->tabResultExame = $this->entityManager->getRepository(Repositories::SST_TABRESULTEXAME)->findOneBy(array('nrorg' => $this->operador()["NRORG"], 'dstabresultexame' => substr($this->naturezaexame->getNmnaturezaexame(),0,50)));
    }
  }

  // TODO: Foreach
  public function setExameFichaMed()
  {
    $sql = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SST_EXAMEFICHAMED);
      
    foreach ($this->exame() as $exame) {
      $sql->execute([
        "NREXAME" => $this->nrExame(),
        "NMEXAMEFICHAMED" => $this->naturezaexame->getNmnaturezaexame(),
        "IDEXAMEREFSEQ" => $exame["ordExame"],
        "IDRESULTNORMAL" => $this->idResultNormal(),
        "IDOCUPACIONAL" => "N",
        "DTREALIZACAOEXAME" => $exame["dtExm"],
        "CDPROCTUSS" => $exame["procRealizado"],
        "OBSPROCTUSS" => $exame["obsProc"],
        "NRORG" => $this->operador()["NRORG"],
        "CDOPERINCLUSAO" => $this->operador()["CDOPERADOR"],
        "NRPARCNEGOCIO" => $this->parcNegocio->getNrparcnegocio(),
        "NRTABRESULTEXAME" => $this->tabResultExame->getNrtabresultexame(),
      ]);
    
    }
  }

  public function setMedicoResponsavel()
  {
    $this->parcNegocio = $this->entityManager->getRepository(Repositories::PARCNEGOCIO)->findOneBy(array('nrorg' => $this->operador()["NRORG"], 'nmprincipalparc' => $this->medico()["nmMed"]));
    if(!$this->parcNegocio){
      $parcNegocio = $this->entityManager
        ->getConnection()
        ->prepare(Queries::PARCNEGOCIO);
      $parcNegocio->execute([
        "NRORG" => $this->operador()["NRORG"],
        "NOME" => $this->medico()["nmMed"],
        "NRCRM" => $this->medico()["nrCRM"],
        "CDOPERADOR" => $this->operador()["CDOPERADOR"],
      ]);
  
      $gpePessoa = $this->entityManager
        ->getConnection()
        ->prepare(Queries::GPE_PESSOA);
      $gpePessoa->execute([
        "NRORG" => $this->operador()["NRORG"],
        "CDOPERADOR" => $this->operador()["CDOPERADOR"],
      ]);
  
      $gpePessoah = $this->entityManager
        ->getConnection()
        ->prepare(Queries::GPE_PESSOAH);
      $gpePessoah->execute([
        "NRORG" => $this->operador()["NRORG"],
        "COMPETENCIA" => $this->operador()["DTMESCOMPETENC"],
        "NOME" => $this->medico()["nmMed"],
        "NRCRM" => $this->medico()["nrCRM"],
        "UFCRM" => $this->medico()["ufCRM"],
        "CDOPERADOR" => $this->operador()["CDOPERADOR"],
      ]);
      
      $this->parcNegocio = $this->entityManager->getRepository(Repositories::PARCNEGOCIO)->findOneBy(array('nrorg' => $this->operador()["NRORG"], 'nmprincipalparc' => $this->medico()["nmMed"]));
    }
  }

  public function vinculoExists()
  {
    if ($this->nrVinculom() == null) {
      return false;
    }

    return true;
  }

  public function fichaMedicaExists()
  {
    $fichaMedica = $this->getFichaMedicaVinculo();

    if (empty($fichaMedica)) {
      return false;
    }

    return true;
  }

  private function getFichaMedicaVinculo()
  {
    $fichaMedica = $this->entityManager
      ->getRepository(Repositories::SST_FICHAMEDICA)
      ->findOneBy(
        array(
          'nrorg' => $this->operador()["NRORG"], 
          'nrvinculom' => $this->nrVinculom(),
          'dthrprevfichamed' => DateUtil::getDataDeString($this->aso()["dtAso"],DateUtil::FORMATO_BRASILEIRO,true),
        )
      );
    
    return is_object($fichaMedica) ? $fichaMedica->getNrfichamedica() : null;
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
    $ideEvento = (array) $this->parameters["EVTMONIT"]["ideEvento"];

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
    $ideEmpregador = (array) $this->parameters["EVTMONIT"]["ideEmpregador"];

    return [
      "ideEmpregador" => $ideEmpregador,
      "tpInsc" => $ideEmpregador["tpInsc"],
      "nrInsc" => $ideEmpregador["nrInsc"],
    ];
  }

  public function ideVinculo(): array
  {
    $ideVinculo = (array) $this->parameters["EVTMONIT"]["ideVinculo"];

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

  public function exMedOcup(): array
  {
    $exMedOcup = (array) $this->parameters["EVTMONIT"]["exMedOcup"];
    
    $this->naturezaexame = $this->entityManager->getRepository(Repositories::SST_NATUREZAEXAME)->findOneBy(array('nrorg' => array($this->operador()["NRORG"], 0), 'cdesocial' => $exMedOcup["tpExameOcup"]));
    
    if (!$this->naturezaexame) {
        throw new \Exception('Não foi encontrada natureza do exame com o código ' . $exMedOcup["tpExameOcup"], 10);
    }

    return [
      "exMedOcup" => $exMedOcup,
      "tpExameOcup" => $exMedOcup["tpExameOcup"],
    ];
  }

  public function aso(): array
  {
    $aso = (array) $this->exMedOcup()["exMedOcup"]["aso"];
    
    $aso["dtAso"] = strtotime($aso["dtAso"]);
    $aso["dtAso"] = date("Y/m/d", $aso["dtAso"]);
    $aso["dtAso"] = \DateTime::createFromFormat(
      "Y/m/d",
      $aso["dtAso"]
    )->format("d/m/Y");

    return [
      "aso" => $aso,
      "dtAso" => $aso["dtAso"],
      "resAso" => isset($aso["resAso"]) ? $aso["resAso"] : 1,
    ];
  }

  public function exame(): array
  {
    $exames = array();
    $result = array();
    
    $tagExame = $this->aso()["aso"]["exame"];
    
    if (is_array($tagExame)) {
      $exames = $tagExame;
    } else {
      $exames[] = $tagExame;
    }

    $ordExameValue = [
      1 => "R",
      2 => "S",
    ];

    $indResultValue = [
      1 => "N",
      2 => "A",
      3 => "E",
      4 => "G",
    ];
    
    foreach ($exames as $exame) {
      $exame = (array) $exame;
      
      $exame["dtExm"] = strtotime($exame["dtExm"]);
      $exame["dtExm"] = date("Y/m/d", $exame["dtExm"]);
      $exame["dtExm"] = \DateTime::createFromFormat(
        "Y/m/d",
        $exame["dtExm"]
      )->format("d/m/Y");
  
      $result[] = [
        "dtExm" => $exame["dtExm"],
        "procRealizado" => $exame["procRealizado"],
        "obsProc" => isset($exame["obsProc"]) ? $exame["obsProc"] : null,
        "ordExame" => isset($exame["ordExame"])
          ? $ordExameValue[$exame["ordExame"]]
          : "S",
        "indResult" => isset($exame["indResult"])
          ? $indResultValue[$exame["indResult"]]
          : "N",
      ];
    }
    
    return $result;
  }

  public function medico(): array
  {
    $medico = (array) $this->aso()["aso"]["medico"];

    $nmMed_utf8 = utf8_decode((string) $medico["nmMed"]);

    return [
      "medico" => $medico,
      "nmMed" => SpecialCharacters::remove($nmMed_utf8),
      "nrCRM" => $medico["nrCRM"],
      "ufCRM" => $medico["ufCRM"],
    ];
  }

  public function respMonit(): array
  {
    $respMonit = (array) $this->exMedOcup()["exMedOcup"]["respMonit"];

    $nmResp_utf8 = utf8_decode((string) $respMonit["nmResp"]);

    return [
      "respMonit" => $respMonit,
      "cpfResp" => isset($respMonit["cpfResp"]) ? $respMonit["cpfResp"] : null,
      "nmResp" => SpecialCharacters::remove($nmResp_utf8),
      "nrCRM" => $respMonit["nrCRM"],
      "ufCRM" => $respMonit["ufCRM"],
    ];
  }

  public function idResultNormal(): string
  {
    return $this->exame()[0]["indResult"] == 1 ? "S" : "N";
  }

  public function nrVinculom()
  {
    $vinculo = $this->entityManager
      ->getRepository(Repositories::GPE_VINCULOM)
      ->retornaVinculosAtivosEInativosPorCPF(
        $this->operador()["NRORG"],
        $this->ideVinculo()["cpfTrab"],
        null,
        $this->operador()["DTMESCOMPETENC"],
        $this->ideVinculo()["codCateg"]
      );

    return isset($vinculo[0]) ? $vinculo[0]->getNrvinculom() : null;
  }

  public function nrExame(): int
  {
    $nrExame = $this->entityManager
      ->getConnection()
      ->prepare(Queries::SELECT_SST_EXAME_MAX);
    $nrExame->execute([
      "NRORG" => $this->operador()["NRORG"],
    ]);

    return (int) $nrExame->fetchAll()[0]["NREXAME"];
  }
}

class Queries
{
  const PARCNEGOCIO = "
    INSERT INTO PARCNEGOCIO 
           (NRPARCNEGOCIO, NRORG, NMPRINCIPALPARC, NMSECUNDARIPARC, NRINSCRICAOPARC, IDATIVO, 
           DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, CDTIPOPARCPRINCIPAL, CDTIPOINSCRICAO, 
           IDPESSOAFISICA, IDINSTITUICAO, IDPARCFUNDIDO) 
    VALUES ((SELECT NVL(MAX(NRPARCNEGOCIO), 0) + 1 AS NRPARCNEGOCIO FROM PARCNEGOCIO WHERE NRORG = :NRORG), 
            :NRORG , :NOME, :NOME, :NRCRM, 'S', SYSDATE, :NRORG, :CDOPERADOR, 'PESSOA', 'LIVRE', 'S', 'N', 'N')
  ";

  const GPE_PESSOA = "
    INSERT INTO GPE_PESSOA 
           (NRPESSOA, NRORG, NRPARCNEGOCIO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO) 
    VALUES ((SELECT NVL(MAX(NRPESSOA), 0) + 1 FROM GPE_PESSOA WHERE NRORG = :NRORG), :NRORG, 
           (SELECT MAX(NRPARCNEGOCIO) AS NRPARCNEGOCIO FROM PARCNEGOCIO WHERE NRORG = :NRORG), SYSDATE, :NRORG, :CDOPERADOR)
  ";

  const GPE_PESSOAH = "
    INSERT INTO GPE_PESSOAH 
           (NRPESSOAH, NRPESSOA, NRORG, DTMESCOMPETENC, NMPESSOA, NRINSCRCONSREG, SGUFCONSREG, DTINCLUSAO, 
           NRORGINCLUSAO, CDOPERINCLUSAO) 
    VALUES ((SELECT NVL(MAX(NRPESSOAH), 0) + 1 FROM GPE_PESSOAH WHERE NRORG = :NRORG), 
           (SELECT MAX(NRPESSOA) FROM GPE_PESSOA WHERE NRORG = :NRORG), :NRORG, :COMPETENCIA, :NOME, :NRCRM, 
           :UFCRM, SYSDATE, :NRORG, :CDOPERADOR)
  ";

  const SST_FICHAMEDICA = "
    INSERT INTO SST_FICHAMEDICA 
           (NRORG, NRFICHAMEDICA, NRVINCULOM, NRPARCNEGOCIO, IDNEXOCAUSAL, IDBENEFICIO, IDEMISSAOCAT, IDATIVO, 
           NRORGINCLUSAO, DTINCLUSAO, CDOPERINCLUSAO, DTHRPREVFICHAMED, NRNATUREZAEXAME) 
    VALUES (:NRORG, (SELECT NVL(MAX(NRFICHAMEDICA), 0) + 1 AS NRFICHAMEDICA FROM SST_FICHAMEDICA WHERE NRORG = :NRORG), 
            :NRVINCULOM, :NRPARCNEGOCIO, 
            'N', 'N', 'S', 'S', :NRORG, SYSDATE, :CDOPERINCLUSAO, :DTHRPREVFICHAMED, :NRNATUREZAEXAME)
  ";

  const SST_TABRESULTEXAME = "
    INSERT INTO SST_TABRESULTEXAME 
           (NRTABRESULTEXAME, NRORG, DSTABRESULTEXAME, IDRESULTEXAME, IDAPTO, IDATIVO, 
           NRORGINCLUSAO, DTINCLUSAO, CDOPERINCLUSAO) 
    VALUES ((SELECT NVL(MAX(NRTABRESULTEXAME), 0) + 1 AS NRTABRESULTEXAME FROM SST_TABRESULTEXAME), 
            :NRORG, :DSTABRESULTEXAME, :IDRESULTEXAME, :IDAPTO, 'S', :NRORG, SYSDATE, 
            :CDOPERINCLUSAO)
  ";

  const SST_EXAMEFICHAMED = "
    INSERT INTO SST_EXAMEFICHAMED 
           (NRORG, NREXAMEFICHAMED, NRFICHAMEDICA, NREXAME, NMEXAMEFICHAMED, IDEXAMEREFSEQ, IDRESULTNORMAL, 
           IDOCUPACIONAL, DTREALIZACAOEXAME, CDPROCTUSS, OBSPROCTUSS, IDATIVO, NRORGINCLUSAO, DTINCLUSAO, 
           CDOPERINCLUSAO, NRPARCNEGOCIO, NRTABRESULTEXAME)
    VALUES (:NRORG, (SELECT MAX(NVL(NREXAMEFICHAMED, 0)) + 1 FROM SST_EXAMEFICHAMED WHERE NRORG = :NRORG), 
            (SELECT MAX(NRFICHAMEDICA) AS NRFICHAMEDICA FROM SST_FICHAMEDICA WHERE NRORG = :NRORG), 
            :NREXAME, :NMEXAMEFICHAMED, :IDEXAMEREFSEQ, :IDRESULTNORMAL, :IDOCUPACIONAL, :DTREALIZACAOEXAME, 
            :CDPROCTUSS, :OBSPROCTUSS, 'S', :NRORG, SYSDATE, :CDOPERINCLUSAO,
            :NRPARCNEGOCIO,
            :NRTABRESULTEXAME)
  ";

  const SELECT_SST_EXAME_MAX = "
    SELECT MAX(NREXAME) AS NREXAME FROM SST_EXAME WHERE NRORG = :NRORG
  ";
}

class SpecialCharacters
{
  private const UTF8 = [
    "/[áàâãªä]/u" => "a",
    "/[ÁÀÂÃÄ]/u" => "A",
    "/[ÍÌÎÏ]/u" => "I",
    "/[íìîï]/u" => "i",
    "/[éèêë]/u" => "e",
    "/[ÉÈÊË]/u" => "E",
    "/[óòôõºö]/u" => "o",
    "/[ÓÒÔÕÖ]/u" => "O",
    "/[úùûü]/u" => "u",
    "/[ÚÙÛÜ]/u" => "U",
    "/ç/" => "c",
    "/Ç/" => "C",
    "/ñ/" => "n",
    "/Ñ/" => "N",
    "/–/" => "-", // UTF-8 hyphen to "normal" hyphen
    "/[’‘‹›]/u" => " ", // Literally a single quote
    "/[“”«»„]/u" => " ", // Double quote
    "/ /" => " ", // nonbreaking space (equiv. to 0x160)
  ];

  public static function remove($string)
  {
    return preg_replace(
      array_keys(self::UTF8),
      array_values(self::UTF8),
      $string
    );
  }
}
