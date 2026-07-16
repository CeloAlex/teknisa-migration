<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\FPA;
use HCM\Util\Repositories;
use HCM\Util\Util;
use PhpOffice\PhpWord\Element\SDT;
use Symfony\Component\DependencyInjection\SimpleXMLElement;
use Zeedhi\Framework\ORM\DateTime;


abstract class ImportacaoXmlEvento {
    
    const MSG_SUCCESS = "Dados do evento NMEVENTO importados corretamente!";
    const MSG_ERRO_XML = "Estrutura do xml do evento incorreta";
    
    const NMEVENTO = '';
    
    protected $nrorg;
    protected $nrorgpadrao;
    protected $dtmescompetencia;
    protected $cdoperador;
    
    protected $nrtipoestrutlegal;
    protected $nrtipoestrutgeren;
    protected $nrtipoestruttomad;
    
    protected $xml;
    
    protected $entityManager;
    
    protected $msgSuccess;
    
    protected $estruturam;
    protected $estruturah;
    protected $parcnegocio;
    protected $comunicaParc;
    protected $gpepessoa;
    protected $gpepessoah;
    protected $ocupacaom;
    protected $ocupacaoh;
    protected $enderecoParc;
    protected $relacionaparc;
    protected $gpevinculom;
    protected $gpevinculoh;
    protected $gpemovimentacao;
    protected $gpealteOcupacao;
    protected $gpealtesalario;
    protected $gpealtesitufunc;
    protected $fpadepvinculo;
    protected $gpealteEscala;
    protected $gpehordiam;
    protected $gpehordiah;
    protected $gpentervaloshorario;
    protected $fpaferias;
    protected $fpagozoferias;
    protected $desFormacao;
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        $this->nrorg = $nrorg;
        $this->nrorgpadrao = $nrorgpadrao;
        $this->dtcompetencia = $dtcompetencia;
        $this->cdoperador = $cdoperador;
        
        $this->nrtipoestrutlegal = FPA::getTipoEstruturaLegalOrg();
        $this->nrtipoestrutgeren = FPA::getTipoEstruturaGerencialOrg();
        $this->nrtipoestruttomad = FPA::getTipoEstruturaTomadorOrg();
        
        $this->xml = new SimpleXMLElement($xml);
        
        $this->entityManager = Util::getEntityManager();
        
        $this->msgSuccess = str_replace('NMEVENTO', static::NMEVENTO, self::MSG_SUCCESS);
        
        $this->estruturam = Repositories::ESTRUTURAM;
        $this->estruturah = Repositories::ESTRUTURAH;
        $this->parcnegocio = Repositories::PARCNEGOCIO;
        $this->comunicaParc = Repositories::COMUNICAPARC;
        $this->gpepessoa = Repositories::GPE_PESSOA;
        $this->gpepessoah = Repositories::GPE_PESSOAH;
        $this->ocupacaom = Repositories::GPE_OCUPACAOM;
        $this->ocupacaoh = Repositories::GPE_OCUPACAOH;
        $this->enderecoParc = Repositories::ENDERECOPARC;
        $this->relacionaparc = Repositories::RELACIONAPARC;
        $this->gpevinculom = Repositories::GPE_VINCULOM;
        $this->gpevinculoh = Repositories::GPE_VINCULOH;
        $this->gpemovimentacao = Repositories::GPE_MOVIMENTACAO;
        $this->gpealteOcupacao = Repositories::GPE_ALTEOCUPACAO;
        $this->gpealtesalario = Repositories::GPE_ALTESALARIO;
        $this->gpealtesitufunc = Repositories::GPE_ALTESITUFUNC;
        $this->fpadepvinculo = Repositories::FPA_DEPVINCULO;
        $this->gpealteEscala = Repositories::GPE_ALTEESCALA;
 	    $this->gpeescalatrabm = Repositories::GPE_ESCALATRABM;
 	    $this->gpeescalatrabh = Repositories::GPE_ESCALATRABH;
 	    $this->gpeturno = Repositories::GPE_TURNO;
 	    $this->gpehordiam = Repositories::GPE_HORDIAM;
 	    $this->gpehordiah = Repositories::GPE_HORDIAH;
 	    $this->gpehorarioturno = Repositories::GPE_HORARIOTURNO;
 	    $this->gpentervaloshorario = Repositories::GPE_INTERVALOSHORARIO;
 	    $this->fpaferias = Repositories::FPA_FERIAS;
 	    $this->fpagozoferias = Repositories::FPA_GOZOFERIAS;
 	    $this->desFormacao = Repositories::DES_FORMACAO;
    }
    
    abstract protected function importarXml();
    
    public function getOperacaoEventoCadastro($tagEvento) {
        if ($tagEvento->inclusao) {
            $operacao = 'inclusao';
        }else if ($tagEvento->alteracao) {
            $operacao = 'alteracao';
        } else {
            throw new \Exception("O arquivo não pode ser importado, não corresponde a um arquivo de inclusão ou alteração", 10);
        }
        return $operacao;
    }
    
    public function consultaDadoRF($NrInscricao){
        /*
          $opc = array('proxy_host'=>"192.168.122.3",
          'proxy_port'=>8080,
          'proxy_login'=>"",
          'proxy_password'=>"");
        */
        $client = new \SoapClient('http://www.soawebservices.com.br/webservices/producao/cdc/cdc.asmx?WSDL');

        if (strlen($NrInscricao) == 14)
            $function = 'PessoaJuridicaNFe';
        else
            $function = 'PessoaFisicaSimplificada';

        $arguments = array(array('Credenciais' => array('Email' => 'guilherme.martins@teknisa.com',
                                                          'Senha' => 'TxVLWUB6'),
                                   'Documento'    => $NrInscricao));
        $options = array('location' => 'http://www.soawebservices.com.br/webservices/producao/cdc/cdc.asmx');

        try {
            $result = $client->__soapCall($function, $arguments, $options);
        }catch (\Exception $e) {
            return array("Status" => false, "CONEXAO" => true);
        }

        $result = json_encode($result);
        $resultadoConsulta = json_decode($result,true);
        return $resultadoConsulta[$function.'Result'];
    }
    
    public function verificaEstruturaMesmaInscricao($nrInsc, $nrtipoestrutura, $nrorg, $dtcompetencia){
        $estrutura = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $nrInsc, $nrtipoestrutura, $dtcompetencia);
        return $estrutura;
    }
    
    public function verificaEstruturaMatrizMesmaInscricao($nrInsc, $nrtipoestrutura, $nrorg, $dtcompetencia){
        $estrutura = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaMatrizPorRaizCnpj($nrorg, $nrInsc, $nrtipoestrutura, $dtcompetencia);
        return $estrutura;
    }
    
    public function ordenaDados($intervalos){
        $sortArray = array();
        
        foreach($intervalos as $k => $intervalo){
            $intervalo = (array) $intervalo;
            foreach($intervalo as $key=>$value){
                if(!isset($sortArray[$key])){
                    $sortArray[$key] = array();
                }
                $sortArray[$key][] = $value;
            }
        }
        $orderby = "iniInterv";

        array_multisort($sortArray[$orderby],SORT_ASC,$intervalos);
        
        return $intervalos;
    }
    
    public function alterDateFormat($data, $tpdata = 1){
        if($tpdata == 1){
            $year = substr($data, 0, 4);
            $month = substr($data, 5, 2);
            $newDate = '01/'.$month.'/'.$year;
            
            return $newDate;
        }else if($tpdata == 2){
            $year = substr($data, 0, 4);
            $month = substr($data, 5, 2);
            $day = substr($data, 8, 2);
            
            $newDate = $day.'/'.$month.'/'.$year;
            
            return $newDate; 
        }
    }
    
    public function getHoraDeMinuto($minutos){
        /*if($minutos < 60){
            $hora = '00'.$minutos;
        }else if($minutos == 60){
            $hora = '0100';
        }else{
            // Arredonda a hora
            $h = floor($minutos / 60); 
            $m = ($minutos - ($h * 60)) / 100; 
            $horas = $h + $m; 
            // Matemática da quinta série
            // Detalhe: Aqui também pode se usar o abs()
            if ($minutos < 0)
                $horas *= -1; 
            // Separa a hora dos minutos
            $sep = explode('.', $horas); 
            $h = $sep[0]; 
            
            if (empty($sep[1])){
                $m = '00'; 
            }else if(strlen($sep[1]) < 2){
                $m = $m . '0'; 
            }else{
                $m = $sep[1]; 
            }
            
            $hora = '0'.$h.$m;  
        }*/
        $hora = DateUtil::convertMinutesToHoursMins($minutos);
        $hora = str_replace(':','',$hora);
        
        return $hora;
    }
    
    
    public function retornaQtDias($date1, $date2){
        $timeDate1 = strtotime($date1->format('Y-m-d'));
        $timeDate2 = strtotime($date2->format('Y-m-d'));
        $time = ($timeDate2 - $timeDate1)/3600;
        $days = $time/24;
        
        return $days + 1;
    }
    
    public function retonaAtivo($data){
        $dataFormat = !empty($data) ? DateTime::createFromFormat('d/m/Y', $data) : '';
        $dataAtual = new DateTime();
        
        if(empty($data) || strtotime($dataFormat->format('Y-m-d')) > strtotime($dataAtual->format('Y-m-d'))){
            return 'S';
        }else{
            return 'N';
        }
        
    }
    
    public function montaNomeEstrutura($nomeMatriz, $nrInsc, $infixo){
        if($nomeMatriz == ''){
            $nome = substr($infixo.' '.$nrInsc, 0, 100);
        }else{
            $sufixo = ' - '.$infixo.' '.$nrInsc.'';
            $prefixo = substr($nomeMatriz, 0, (100 - strlen($sufixo)));
            $nome = $prefixo.$sufixo;
        }
        
        return $nome;
    }
    
    public function decompoeNomePessoa($nmpessoa){
        $arrayNmpessoa = explode(' ', $nmpessoa);
        $nomeMeio      = '';

        $primeiroNome = $arrayNmpessoa[0];
        for ($i = 1; $i < count($arrayNmpessoa) - 1; $i++) {
            $nomeMeio .= ' ' . $arrayNmpessoa[$i];
            $nomeMeio = trim($nomeMeio);
        }
        $ultimoNome = $arrayNmpessoa[count($arrayNmpessoa) - 1];
        $nomeMeio   = ($nomeMeio) ? : $ultimoNome;
        return array($primeiroNome, $nomeMeio, $ultimoNome);
    }
    
    public function getPronomeTratamento($cdEstadoCivil,$idSexoPessoa) {
        if ($idSexoPessoa == 'M'){
            $pronomeTratamento = 'Sr.';
            return $pronomeTratamento;
        }
        else if ($idSexoPessoa == 'F' && $cdEstadoCivil == 'C'){
            $pronomeTratamento = 'Sra.';
            return $pronomeTratamento;
        }
        else {
            $pronomeTratamento = 'Srta.';
            return $pronomeTratamento;
        }
    }
    
    public function retonarTipoEstruturaInserida($tipoestruturaLotacao){
        foreach($tipoestruturaLotacao as $tipo){
            if($tipo->getNrtipoestrutura() == $this->nrtipoestrutlegal){
                return array('tipo'   => 'LEGAL',
                             'numero' => $this->nrtipoestrutlegal);
            }
            if($tipo->getNrtipoestrutura() == $this->nrtipoestruttomad){
                return array('tipo'   =>'TOMADOR',
                             'numero' => $this->nrtipoestruttomad);
            }            
        }
    }
    
    public function retornaCondicaoFisica($infoDeficiencia){
        $deficiencias = $infoDeficiencia['defFisica'].$infoDeficiencia['defVisual'].$infoDeficiencia['defAuditiva'].$infoDeficiencia['defMental'].$infoDeficiencia['defIntelectual'].$infoDeficiencia['reabReadap'];

        if(substr_count($deficiencias, 'S') > 1){
            return 6;
        }else if($infoDeficiencia['defFisica'] == 'S'){
            return 2;
        }else if($infoDeficiencia['defVisual'] == 'S'){
            return 4;
        }else if($infoDeficiencia['defAuditiva'] == 'S'){
            return 3;
        }else if($infoDeficiencia['defMental'] == 'S'){
            return 5;
        }else if($infoDeficiencia['defIntelectual'] == 'S'){
            return 8;
        }else if($infoDeficiencia['reabReadap'] == 'S'){
            return 7;
        }else{
            return 1;
        }
    }
    
    public function validaPIS($pis) {
        $multiplicadorBase = "3298765432";
        $total = 0;
        $resto = 0;
        $multiplicando = 0;
        $multiplicador = 0;
        $digito = 99;
        
        // Retira a mascara
        $numeroPIS = preg_replace('/[^0-9]/', '', $pis);
        
        if (strlen($numeroPIS) !== 11 || 
            $numeroPIS === "00000000000" || 
            $numeroPIS === "11111111111" || 
            $numeroPIS === "22222222222" || 
            $numeroPIS === "33333333333" || 
            $numeroPIS === "44444444444" || 
            $numeroPIS === "55555555555" || 
            $numeroPIS === "66666666666" || 
            $numeroPIS === "77777777777" || 
            $numeroPIS === "88888888888" || 
            $numeroPIS === "99999999999") {
            return false;
        } else {
            for ($i = 0; $i < 10; $i++) {
                $multiplicando = intval( substr($numeroPIS, $i, 1));
                $multiplicador = intval( substr($multiplicadorBase, $i, 1));
                $multiplicacao = $multiplicando * $multiplicador;
                $total += $multiplicacao;
            }
        
            $resto = 11 - $total % 11;
            $resto = $resto === 10 || $resto === 11 ? 0 : $resto;
        
            $digito = intval(substr($numeroPIS, 10));
            return $resto === $digito;
        }
    }
    
    public function novoParcNegocio($nrorg, $nmprincipalparc, $nmsecundariparc, $cdtipoparceiro, $idpessoafisica, $idinstituicao,
                                    $cdtipoinscricao, $nrinscricaoparc, $dtnascifundparc, $idativo, $idparcfundido = 'N'){
        
        $parceiro = new $this->parcnegocio;
        $parceiro->setNrorg($nrorg);
        $parceiro->setIdativo($idativo);
        $parceiro->setNmprincipalparc($nmprincipalparc);
        $parceiro->setNmsecundariparc($nmsecundariparc);
        $parceiro->setCdtipoparcprincipal($cdtipoparceiro);
        $parceiro->setIdpessoafisica($idpessoafisica);
        $parceiro->setIdinstituicao($idinstituicao);
        $parceiro->setCdtipoinscricao($cdtipoinscricao);
        $parceiro->setNrinscricaoparc($nrinscricaoparc);
        $parceiro->setDtnascifundparc($dtnascifundparc);
        $parceiro->setIdparcfundido($idparcfundido);

        $parceiro->setDtinclusao(DateUtil::getDataAtual());
        $parceiro->setNrorginclusao($this->nrorg);
        $parceiro->setCdoperinclusao($this->cdoperador);
        $parceiro->setDtultatu(DateUtil::getDataAtual());
        $parceiro->setNrorgultatu($this->nrorg);
        $parceiro->setCdoperultatu($this->cdoperador);

        $parceiro->setNrparcnegocio(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'PARCNEGOCIO', 1, 12, true));
        
        $this->entityManager->persist($parceiro);
        $this->entityManager->flush();
        
        return $parceiro;
        
    }
    
    public function novaEstrutura($nrtipoestrutura, $dtinivigencia, $idativo, $idoptsimples, $nrparcnegocio, $nmestruturam = null, $cdcnpjestrut = null, $dtfimvigencia = null, $cdintestrutura = null, $nrestruturamold = null, $dsestrutura = null, $cdintestrutexp = null,
                                  $cdintestrutexpfil = null, $cdcentcust = null, $dsurllogoestrutura = null, $nrtpeventoctbl = null, $nrregimeapur = null, $dtesocial = null, $nrgrupoesocial = null, $dtextincao = null, $nrcalendario = null, $cdceiestrut = null, $nmrazsocestrut = null,
                                  $cdnatujuri = null, $cdcnae = null, $nrcaged = null, $cdemprcaixa = null, $idtipoempr = null, $idparticipat = null, $nrpropriempr = null, $nrparcrespinf = null, $nrparcentisin = null, $cdfpas = null, $cdreducont = null, $nmfantasia = null, 
                                  $nmestruturah = null, $cdcpfestrutura = null, $dtbasesindical = null, $cdsindical = null, $cdterceiro = null, $nrclasstribut = null, $vrfap = null, $nrtipotribut = null, $vraliqdeson = null, $cdfederalestrut = null, $nrparcregamb = null, 
                                  $nrparcmonbio = null, $dtiniresamb = null, $dtfimresamb = null, $nrtpobrigaprendiz = null, $nrtpobrigapcd = null, $cdcaepfestrut = null, $codconvenio = null){
        
        $nrorg = $this->nrorg;
        $mesCompetencia = DateUtil::truncateData(DateUtil::getPrimeiroDiaDoMes(DateUtil::getDataDeString($dtinivigencia,DateUtil::FORMATO_BRASILEIRO,true)));
        
        $estruturam = $this->estruturaMestre($nrorg, $idativo, $nrtipoestrutura, $dtinivigencia, $nrparcnegocio, $nmestruturam, $dtfimvigencia, $cdintestrutura, $nrestruturamold, $dsestrutura, $cdintestrutexp,
                                             $cdintestrutexpfil, $cdcentcust, $dsurllogoestrutura, $nrtpeventoctbl, $nrregimeapur, $dtesocial, $nrgrupoesocial);
        $estruturah = $this->estruturaHistorico($nrorg, $idativo, $estruturam->getNrestruturam(), $mesCompetencia, $idoptsimples, $nrparcnegocio, $cdcnpjestrut, $dtextincao, $nrcalendario, $cdceiestrut, $nmrazsocestrut,
                                                $cdnatujuri, $cdcnae, $nrcaged, $cdemprcaixa, $idtipoempr, $idparticipat, $nrpropriempr, $nrparcrespinf, $nrparcentisin, $cdfpas, $cdreducont, $nmfantasia, 
                                                $nmestruturah, $cdcpfestrutura, $dtbasesindical, $cdsindical, $cdterceiro, $nrclasstribut, $vrfap, $nrtipotribut, $vraliqdeson, $cdfederalestrut, $nrparcregamb, 
                                                $nrparcmonbio, $dtiniresamb, $dtfimresamb, $nrtpobrigaprendiz, $nrtpobrigapcd, $cdcaepfestrut, $codconvenio);
        
        return array($estruturam, $estruturah);
    } 
   
    public function estruturaMestre($nrorg, $idativo, $nrtipoestrutura, $dtinivigencia, $nrparcnegocio, $nmestruturam, $dtfimvigencia = null, $cdintestrutura = null, $nrestruturamold = null, $dsestrutura = null, $cdintestrutexp = null,
                                $cdintestrutexpfil = null, $cdcentcust = null, $dsurllogoestrutura = null, $nrtpeventoctbl = null, $nrregimeapur = null, $dtesocial = null, $nrgrupoesocial = null){
                                    
        $estruturam = new $this->estruturam;
        
        $estruturam->setNrorg($nrorg);
        $estruturam->setNrtipoestrutura($nrtipoestrutura);
        $estruturam->setDtinivigencia(DateUtil::getDataDeString($dtinivigencia,DateUtil::FORMATO_BRASILEIRO,true));
        $estruturam->setNrparcnegocio($nrparcnegocio);
        $estruturam->setNmestruturam($nmestruturam);
        $estruturam->setIdativo($idativo);
        
        $estruturam->setDtfimvigencia(DateUtil::getDataDeString($dtfimvigencia,DateUtil::FORMATO_BRASILEIRO,true));
        $estruturam->setCdintestrutura($cdintestrutura);
        $estruturam->setNrestruturamold($nrestruturamold);
        // $estruturam->setDsestrutura($dsestrutura);
        // $estruturam->setCdintestrutexp($cdintestrutexp);
        // $estruturam->setCdintestrutexpfil($cdintestrutexpfil);
        // $estruturam->setCdcentcust($cdcentcust);
        // $estruturam->setDsurllogoestrutura($dsurllogoestrutura);
        $estruturam->setNrtpeventoctbl($nrtpeventoctbl);
        // $estruturam->setNrregimeapur($nrregimeapur);
        // $estruturam->setDtesocial($dtesocial);
        // $estruturam->setNrgrupoesocial($nrgrupoesocial);       
        

        $estruturam->setDtinclusao(DateUtil::getDataAtual());
        $estruturam->setNrorginclusao($this->nrorg);
        $estruturam->setCdoperinclusao($this->cdoperador);
        $estruturam->setDtultatu(DateUtil::getDataAtual());
        $estruturam->setNrorgultatu($this->nrorg);
        $estruturam->setCdoperultatu($this->cdoperador);

        $estruturam->setNrestruturam(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'ESTRUTURAM', 1, 12, true));

        $this->entityManager->persist($estruturam);
        $this->entityManager->flush();
    
        return $estruturam;
        
    }
    
    public function estruturaHistorico($nrorg, $idativo, $nrestruturam, $mesCompetencia, $idoptsimples, $nrparcnegocio, $cdcnpjestrut = null, $dtextincao = null, $nrcalendario = null, $cdceiestrut = null, $nmrazsocestrut = null,
                                  $cdnatujuri = null, $cdcnae = null, $nrcaged = null, $cdemprcaixa = null, $idtipoempr = null, $idparticipat = null, $nrpropriempr = null, $nrparcrespinf = null, $nrparcentisin = null, $cdfpas = null, $cdreducont = null, $nmfantasia = null, 
                                  $nmestruturah = null, $cdcpfestrutura = null, $dtbasesindical = null, $cdsindical = null, $cdterceiro = null, $nrclasstribut = null, $vrfap = null, $nrtipotribut = null, $vraliqdeson = null, $cdfederalestrut = null, $nrparcregamb = null, 
                                  $nrparcmonbio = null, $dtiniresamb = null, $dtfimresamb = null, $nrtpobrigaprendiz = null, $nrtpobrigapcd = null, $cdcaepfestrut = null, $codconvenio = null){
        
        $estruturah = new $this->estruturah;
        
        $estruturah->setNrorg($nrorg);
        $estruturah->setNrestruturam($nrestruturam);
        $estruturah->setDtmescompetenc($mesCompetencia);
        $estruturah->setCdcnpjestrut($cdcnpjestrut);
        $estruturah->setIdoptsimples($idoptsimples);
        
        $estruturah->setDtextincao(DateUtil::getDataDeString($dtextincao));
        $estruturah->setNrcalendario($nrcalendario);
        $estruturah->setCdceiestrut($cdceiestrut);
        $estruturah->setNmrazsocestrut($nmrazsocestrut);
        $estruturah->setCdnatujuri($cdnatujuri);
        $estruturah->setCdcnae($cdcnae);
        $estruturah->setNrcaged($nrcaged);
        $estruturah->setCdemprcaixa($cdemprcaixa);
        $estruturah->setIdtipoempr($idtipoempr);
        $estruturah->setIdparticipat($idparticipat);
        $estruturah->setNrparcnegocio($nrparcnegocio);
        $estruturah->setNrpropriempr($nrpropriempr);
        $estruturah->setNrparcrespinf($nrparcrespinf);
        $estruturah->setNrparcentisin($nrparcentisin);
        $estruturah->setCdfpas($cdfpas);
        $estruturah->setCdreducont($cdreducont);
        $estruturah->setNmfantasia($nmfantasia);
        $estruturah->setNmestruturah($nmestruturah);
        $estruturah->setCdcpfestrutura($cdcpfestrutura);
        $estruturah->setDtbasesindical($dtbasesindical);
        $estruturah->setCdsindical($cdsindical);
        $estruturah->setCdterceiro($cdterceiro);
        $estruturah->setNrclasstribut($nrclasstribut);
        $estruturah->setVrfap($vrfap);
        $estruturah->setNrtipotribut($nrtipotribut);
        $estruturah->setVraliqdeson($vraliqdeson);
        $estruturah->setCdfederalestrut($cdfederalestrut);
        $estruturah->setIdativo($idativo);
        $estruturah->setNrparcregamb($nrparcregamb);
        $estruturah->setNrparcmonbio($nrparcmonbio);
        $estruturah->setDtiniresamb($dtiniresamb);
        $estruturah->setDtfimresamb($dtfimresamb);
        // $estruturah->setNrtpobrigaprendiz($nrtpobrigaprendiz);
        // $estruturah->setNrtpobrigapcd($nrtpobrigapcd);
        $estruturah->setCdcaepfestrut($cdcaepfestrut);
        // $estruturah->setCodconvenio($codconvenio);
        
        $estruturah->setDtinclusao(DateUtil::getDataAtual());
        $estruturah->setNrorginclusao($this->nrorg);
        $estruturah->setCdoperinclusao($this->cdoperador);
        $estruturah->setDtultatu(DateUtil::getDataAtual());
        $estruturah->setNrorgultatu($this->nrorg);
        $estruturah->setCdoperultatu($this->cdoperador);

        $estruturah->setNrestruturah(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'ESTRUTURAH', 1, 12, true));

        $this->entityManager->persist($estruturah);
        $this->entityManager->flush();
        
        return $estruturah;
        
    }
    
    public function novaOcupacao($nrtipoocupacao, $dtinivigencia, $dtmescompetenc, $nmocupacaoh, $dtfimvigencia = null, $dtesocial = null, $nrocupacaomsup = null, $cdintegracao = null, 
                                 $nrcbo = null, $dsobjetivocargo = null, $dsatividadescargo = null, $dscondtrabalho = null, $nrtempoexpano = null , $nrtempoexpmes = null){
        
        $ocupacaom = $this->ocupacaoMestre($nrtipoocupacao, $dtinivigencia, $dtfimvigencia, $dtesocial, $nrocupacaomsup);
    
        $ocupacaoh = $this->ocupacaoHistorico($ocupacaom->getNrocupacaom(), $dtmescompetenc, $nmocupacaoh, $cdintegracao, $nrcbo, $dsobjetivocargo, $dsatividadescargo, $dscondtrabalho, $nrtempoexpano , $nrtempoexpmes);
        
        return array($ocupacaom, $ocupacaoh);
    }
    
    public function ocupacaoMestre($nrtipoocupacao, $dtinivigencia, $dtfimvigencia = null, $dtesocial = null, $nrocupacaomsup = null){
        
        $ocupacaom = new $this->ocupacaom;
        
        $ocupacaom->setNrorg($this->nrorg);
        $ocupacaom->setNrtipoocupacao($nrtipoocupacao);
        $ocupacaom->setDtinivigencia(DateUtil::getDataDeString($dtinivigencia, DateUtil::FORMATO_BRASILEIRO, true));
        $ocupacaom->setDtfimvigencia(DateUtil::getDataDeString($dtfimvigencia, DateUtil::FORMATO_BRASILEIRO, true));
        // $ocupacaom->setDtesocial($dtesocial);
        // $ocupacaom->setNrocupacaomsup($nrocupacaomsup);
        
        $ocupacaom->setDtinclusao(DateUtil::getDataAtual());
        $ocupacaom->setCdoperinclusao($this->cdoperador);
        $ocupacaom->setNrorginclusao($this->nrorg);
        $ocupacaom->setDtultatu(DateUtil::getDataAtual());
        $ocupacaom->setCdoperultatu($this->cdoperador);
        $ocupacaom->setNrorgultatu($this->nrorg);
        
        $ocupacaom->setNrocupacaom(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_OCUPACAOM', 1, 12, true));
        
        $this->entityManager->persist($ocupacaom);
        $this->entityManager->flush();
        
        return $ocupacaom; 
    }
    
    public function ocupacaoHistorico($nrocupacaom, $dtmescompetenc, $nmocupacaoh, $cdintegracao = null, $nrcbo = null, $dsobjetivocargo = null, $dsatividadescargo = null, $dscondtrabalho = null, $nrtempoexpano = null , $nrtempoexpmes = null){
        
        $ocupacaoh = new $this->ocupacaoh;
        
        $ocupacaoh->setNrorg($this->nrorg);
        $ocupacaoh->setNrocupacaom($nrocupacaom);
        $ocupacaoh->setDtmescompetenc(DateUtil::getDataDeString($dtmescompetenc));
        $ocupacaoh->setNmocupacaoh($nmocupacaoh);
        $ocupacaoh->setCdintegracao($cdintegracao);
        $ocupacaoh->setNrcbo($nrcbo);
        // $ocupacaoh->setDsobjetivocargo($dsobjetivocargo);
        // $ocupacaoh->setDsatividadescargo($dsatividadescargo);
        // $ocupacaoh->setDscondtrabalho($dscondtrabalho);
        // $ocupacaoh->setNrtempoexpano($nrtempoexpano);
        // $ocupacaoh->setNrtempoexpmes($nrtempoexpmes);
        
        $ocupacaoh->setDtinclusao(DateUtil::getDataAtual());
        $ocupacaoh->setCdoperinclusao($this->cdoperador);
        $ocupacaoh->setNrorginclusao($this->nrorg);
        $ocupacaoh->setDtultatu(DateUtil::getDataAtual());
        $ocupacaoh->setCdoperultatu($this->cdoperador);
        $ocupacaoh->setNrorgultatu($this->nrorg);
        
        $ocupacaoh->setNrocupacaoh(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_OCUPACAOH', 1, 12, true));
        
        $this->entityManager->persist($ocupacaoh);
        $this->entityManager->flush();
        
        return $ocupacaoh;
    }
    
    public function novoHorario($nrorg, $dtinivigencia, $dtmescompetenc, $nmhordiah, $idtipohorario, $dtfimvigencia = null, $cdintegracao = null, $hrinicoletamarcacao = null){
        
        $gpehordiam = $this->horarioMestre($nrorg, $dtinivigencia, $dtfimvigencia, $cdintegracao);
    
        $gpehordiah = $this->horarioHistorico($nrorg, $gpehordiam->getNrhordiam(), $dtmescompetenc, $nmhordiah, $idtipohorario, $hrinicoletamarcacao);
        
        return array($gpehordiam, $gpehordiah);
        
    }
    
    public function horarioMestre($nrorg, $dtinivigencia, $dtfimvigencia = null, $cdintegracao = null){
        
        $gpehordiam = new $this->gpehordiam;
        
        $gpehordiam->setNrorg($nrorg);
        $gpehordiam->setDtfimvigencia($dtfimvigencia);
        $gpehordiam->setDtinivigencia($dtinivigencia);
        $gpehordiam->setCdintegracao($cdintegracao);
        
        $gpehordiam->setDtinclusao(DateUtil::getDataAtual());
        $gpehordiam->setCdoperinclusao($this->cdoperador);
        $gpehordiam->setNrorginclusao($this->nrorg);
        $gpehordiam->setDtultatu(DateUtil::getDataAtual());
        $gpehordiam->setCdoperultatu($this->cdoperador);
        $gpehordiam->setNrorgultatu($this->nrorg);
        
        $gpehordiam->setNrhordiam(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_HORDIAM', 1, 12, true));
        
        $this->entityManager->persist($gpehordiam);
        $this->entityManager->flush();
        
        return $gpehordiam;
        
    }
    
    public function horarioHistorico($nrorg, $nrhordiam, $dtmescompetenc, $nmhordiah, $idtipohorario, $hrinicoletamarcacao = null){
        
        $gpehordiah = new $this->gpehordiah;
        
        $gpehordiah->setNrorg($nrorg);
        $gpehordiah->setNrhordiam($nrhordiam);
        $gpehordiah->setDtmescompetenc($dtmescompetenc);
        $gpehordiah->setNmhordiah($nmhordiah);
        $gpehordiah->setIdtipohorario($idtipohorario);
        $gpehordiah->setHrinicoletamarcacao($hrinicoletamarcacao);
        
        $gpehordiah->setDtinclusao(DateUtil::getDataAtual());
        $gpehordiah->setCdoperinclusao($this->cdoperador);
        $gpehordiah->setNrorginclusao($this->nrorg);
        $gpehordiah->setDtultatu(DateUtil::getDataAtual());
        $gpehordiah->setCdoperultatu($this->cdoperador);
        $gpehordiah->setNrorgultatu($this->nrorg);
        
        $gpehordiah->setNrhordiah(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_HORDIAH', 1, 12, true));
        
        $this->entityManager->persist($gpehordiah);
        $this->entityManager->flush();
        
        return $gpehordiah; 
    }

    
    public function novaPessoa($nrorg, $nrparcnegocio, $dtmescompetencia, $nmpessoa, $apelido, $nrCertidaoNascimento, $dtNascimento, $idSexo, $nrCondicaoFisica, $nrCPF, $nrCTPS, $nrSerieCTPS, $sgufCTPS, $dtCTPS, $nrPIS, $dtPIS, $nrInscricaoINSS, $nrInscricaoISS, $cdEstadoCivil, 
                               $nrCertidaoCasamento, $dtCasamento, $idIsentoTituloEleitor, $nrTituloEleitor, $nrSecaoEleitoral, $nrZonaEleitoral, $nrHabilitacao, $dtHabilitacao, $dtValidadeHabilitacao, $categoriaHabilitacao, $sgufhabcarpes, $nrCategoriaMilitar, $nrCertificadoReservista, 
                               $dsCertificadoReservista, $dtCertificadoReservista, $cdExpedicaoCertificadoReservista, $nrRaca, $idGrupoSanguineo, $idFatorRH, $cdpais, $sgEstado, $cdMunicipio, $nrRg, $orgaoExpedidorRG, $sgExpedidorRG, $dsLocalExpedicaoRG, $dtExpedicaoRG,
                               $nrNacionalidade, $nrGrauInstrucao, $pronometrat = null, $nranochegapais = null, $nrdocuestrang = null, $idpesnaturaliza = null, $dtnaturalizapes = null, $idposvistoperm = null, $dtpermavisto = null, $nrconselhoreg = null, $nrinscrconsreg = null, 
                               $dtexconsreg = null, $sgufconsreg = null, $cdtpbaixapag = null, $nrlivrocertnasc = null, $nrfolhacertnasc = null, $dscomplcertnasc = null,$nrregctpspes = null, $nrclassestrang = null, $dsexpdocestr = null, $dtchegadapais = null, $idcotapcd = null,
                               $nrnitpessoa = null){
        
        $pessoa = $this->pessoaMestre($nrorg, $nrparcnegocio);
        $pessoah = $this->pessoaHistorico($nrorg, $pessoa->getNrpessoa(), $dtmescompetencia, $nmpessoa, $apelido, $nrCertidaoNascimento, $dtNascimento, $idSexo, $nrCondicaoFisica, $nrCPF, $nrCTPS, $nrSerieCTPS, $sgufCTPS, $dtCTPS, $nrPIS, $dtPIS, $nrInscricaoINSS, $nrInscricaoISS, 
                                        $cdEstadoCivil, $nrCertidaoCasamento, $dtCasamento, $idIsentoTituloEleitor, $nrTituloEleitor, $nrSecaoEleitoral, $nrZonaEleitoral, $nrHabilitacao, $dtHabilitacao, $dtValidadeHabilitacao, $sgufhabcarpes, $categoriaHabilitacao, $nrCategoriaMilitar, 
                                        $nrCertificadoReservista, $dsCertificadoReservista, $dtCertificadoReservista, $cdExpedicaoCertificadoReservista, $nrRaca, $idGrupoSanguineo, $idFatorRH, $cdpais, $sgEstado, $cdMunicipio, $nrRg, $orgaoExpedidorRG, $sgExpedidorRG,
                                        $dsLocalExpedicaoRG, $dtExpedicaoRG, $nrNacionalidade, $nrGrauInstrucao, $pronometrat, $nranochegapais, $nrdocuestrang, $idpesnaturaliza, $dtnaturalizapes, $idposvistoperm, $dtpermavisto, $nrconselhoreg, $nrinscrconsreg, $dtexconsreg,
                                        $sgufconsreg, $cdtpbaixapag, $nrlivrocertnasc, $nrfolhacertnasc, $dscomplcertnasc,$nrregctpspes, $nrclassestrang, $dsexpdocestr, $dtchegadapais, $idcotapcd, $nrnitpessoa);
                                        
        return array($pessoa, $pessoah);
    }
    
    public function pessoaMestre($nrorg, $nrparcnegocio) {
        $pessoa = new $this->gpepessoa;

        $pessoa->setNrorg($nrorg);
        $pessoa->setNrparcnegocio($nrparcnegocio);

        $pessoa->setDtinclusao(DateUtil::getDataAtual());
        $pessoa->setNrorginclusao($this->nrorg);
        $pessoa->setCdoperinclusao($this->cdoperador);
        $pessoa->setDtultatu(DateUtil::getDataAtual());
        $pessoa->setNrorgultatu($this->nrorg);
        $pessoa->setCdoperultatu($this->cdoperador);

        $pessoa->setNrpessoa(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_PESSOA', 1, 12, true));

        $this->entityManager->persist($pessoa);
        $this->entityManager->flush();
        return $pessoa;
    }
    
    public function pessoaHistorico($nrorg, $nrpessoa, $dtmescompetencia, $nmpessoa, $apelido, $nrCertidaoNascimento, $dtNascimento, $idSexo, $nrCondicaoFisica, $nrCPF, $nrCTPS, $nrSerieCTPS, $sgufCTPS, $dtCTPS, $nrPIS, $dtPIS, $nrInscricaoINSS, $nrInscricaoISS, $cdEstadoCivil, 
                                  $nrCertidaoCasamento, $dtCasamento, $idIsentoTituloEleitor, $nrTituloEleitor, $nrSecaoEleitoral, $nrZonaEleitoral, $nrHabilitacao, $dtHabilitacao, $dtValidadeHabilitacao, $categoriaHabilitacao, $sgufhabcarpes,$nrCategoriaMilitar, $nrCertificadoReservista, 
                                  $dsCertificadoReservista, $dtCertificadoReservista, $cdExpedicaoCertificadoReservista, $nrRaca, $idGrupoSanguineo, $idFatorRH, $cdpais, $sgEstado, $cdMunicipio, $nrRg, $orgaoExpedidorRG, $sgExpedidorRG, $dsLocalExpedicaoRG, $dtExpedicaoRG, $nrNacionalidade, 
                                  $nrGrauInstrucao, $pronometrat = null,  $nranochegapais = null, $nrdocuestrang = null, $idpesnaturaliza = null, $dtnaturalizapes = null, $idposvistoperm = null, $dtpermavisto = null, $nrconselhoreg = null, $nrinscrconsreg = null, $dtexconsreg = null, 
                                  $sgufconsreg = null, $cdtpbaixapag = null, $nrlivrocertnasc = null, $nrfolhacertnasc = null, $dscomplcertnasc = null,$nrregctpspes = null, $nrclassestrang = null, $dsexpdocestr = null, $dtchegadapais = null, $idcotapcd = null, $nrnitpessoa = null){
        
        $pessoah = new $this->gpepessoah;

        //setDadosPrincipais
        list($primeiroNome, $meioNome, $ultimoNome) = self::decompoeNomePessoa($nmpessoa);
        
        $pessoah->setNrorg($nrorg);
        $pessoah->setNrpessoa($nrpessoa);
        $pessoah->setNmpessoa($nmpessoa);
        $pessoah->setDsprinomepess($primeiroNome);
        $pessoah->setDsnomemeiopess((strlen($meioNome)> 20) ? substr($meioNome, 0, 20) : $meioNome);
        $pessoah->setDsultnomepess($ultimoNome);
        $pessoah->setDsapelidopess($apelido);
        $pessoah->setDtmescompetenc($dtmescompetencia);
        $pessoah->setDtnascpessoa($dtNascimento);
        $pessoah->setNrcertnascpes($nrCertidaoNascimento);
        $pessoah->setNrlivrocertnasc($nrlivrocertnasc);
        $pessoah->setNrfolhacertnasc($nrfolhacertnasc);
        $pessoah->setDscomplcertnasc($dscomplcertnasc);

        //setRegistroIdentidade
        $pessoah->setNrcpfpessoa($nrCPF);
        $pessoah->setNrrgpessoa($nrRg);
        $pessoah->setCdexrgpessoa($orgaoExpedidorRG);
        $pessoah->setSgufrgpessoa($sgExpedidorRG);
        $pessoah->setDslocalexrgpes($dsLocalExpedicaoRG);
        $pessoah->setDtexrgpessoa($dtExpedicaoRG);

        //setLocal
        $pessoah->setNrnacionalid($nrNacionalidade);
        $pessoah->setCdpais($cdpais);
        $pessoah->setSgestado($sgEstado);
        $pessoah->setCdmunicipio($cdMunicipio);

        //setImigrante
        $pessoah->setNranochegapais($nranochegapais);
        $pessoah->setNrdocuestrang($nrdocuestrang);
        $pessoah->setIdpesnaturaliza($idpesnaturaliza);
        $pessoah->setDtnaturalizapes($dtnaturalizapes);
        $pessoah->setIdposvistoperm($idposvistoperm);
        $pessoah->setDtpermavisto($dtpermavisto);
        $pessoah->setNrclassestrang($nrclassestrang);
        $pessoah->setDsexpdocestr($dsexpdocestr);
        $pessoah->setDtchegadapais($dtchegadapais ? DateUtil::getDataDeString($dtchegadapais) : null);

        //setDadosCarteiraTrabalho
        $pessoah->setNrctpspessoa($nrCTPS);
        $pessoah->setNrseriectpspes($nrSerieCTPS);
        $pessoah->setSgufctpspes($sgufCTPS);
        $pessoah->setDtctpspessoa($dtCTPS);
        $pessoah->setNrregctpspes($nrregctpspes);

        //setDadosImpostos
        $pessoah->setNrpispaseppes($nrPIS);
        $pessoah->setDtinscpispasep($dtPIS);
        $pessoah->setNrinscinsspes($nrInscricaoINSS);
        $pessoah->setNrinscisspes($nrInscricaoISS);

        //setDadosCivis
        $pessoah->setCdestacivil($cdEstadoCivil);
        $pessoah->setNrcertcasapes($nrCertidaoCasamento);
        $pessoah->setDtcasapessoa($dtCasamento);

        //setDadosEleitorais
        $pessoah->setIdisentituelei($idIsentoTituloEleitor);
        $pessoah->setNrtitueleipes($nrTituloEleitor);
        $pessoah->setNrsecaeleipes($nrSecaoEleitoral);
        $pessoah->setNrzonaeleipes($nrZonaEleitoral);

        //setDadosHabilitacaoVeiculo
        $pessoah->setNrcarthabpes($nrHabilitacao);
        $pessoah->setDthabcartpes($dtHabilitacao);
        $pessoah->setDtvalhabcartpes($dtValidadeHabilitacao);
        $pessoah->setDscateghabcart($categoriaHabilitacao);

        //setDadosMilitares
        $pessoah->setNrcatmilitarpe($nrCategoriaMilitar);
        $pessoah->setNrcertresepes($nrCertificadoReservista);
        $pessoah->setDscategcertrese($dsCertificadoReservista);
        $pessoah->setDtcertresepes($dtCertificadoReservista);
        $pessoah->setCdexcertresepes($cdExpedicaoCertificadoReservista);

        //setDadosFisicos
        $pessoah->setIdsexopessoa($idSexo);
        $pessoah->setNrracapessoa($nrRaca);
        $pessoah->setNrcondfispes($nrCondicaoFisica);
        $pessoah->setIdgrupsangupes($idGrupoSanguineo);
        $pessoah->setIdcotapcd($idcotapcd);
        $pessoah->setIdfatorrhpes($idFatorRH);

        //setDadosAdicionais
        $pessoah->setNrgrauinstr($nrGrauInstrucao);
        $pessoah->setNrconselhoreg($nrconselhoreg);
        $pessoah->setNrinscrconsreg($nrinscrconsreg);
        $pessoah->setDtexconsreg($dtexconsreg);
        $pessoah->setSgufconsreg($sgufconsreg);
        $pessoah->setCdtpbaixapag($cdtpbaixapag);
        $pessoah->setNrnitpessoa($nrnitpessoa);

        if($pronometrat) {
            $pessoah->setDspronometrat($pronometrat);
        }else{
            $pronomeTratamento = $this->getPronomeTratamento($cdEstadoCivil, $idSexo);
            $pessoah->setDspronometrat($pronomeTratamento);
        }

        $pessoah->setDtinclusao(DateUtil::getDataAtual());
        $pessoah->setNrorginclusao($this->nrorg);
        $pessoah->setCdoperinclusao($this->cdoperador);
        $pessoah->setDtultatu(DateUtil::getDataAtual());
        $pessoah->setNrorgultatu($this->nrorg);
        $pessoah->setCdoperultatu($this->cdoperador);

        $pessoah->setNrpessoah(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_PESSOAH', 1, 12, true));
        
        $this->entityManager->persist($pessoah);
        $this->entityManager->flush();
        return $pessoah;
    }
    
    public function novoVinculo($nrPessoa, $dtAdmissaoVinculo, $cdMatricula, $nrTipoVinculom, $nrTipoAdmissao, $nrVinculoEmpregaticio, $dtOpcaoFGTS, $dtAposentadoriaFGTS, $dtPrimeiraAdmissao,$nmVinculom, $nrDiasContratoExp, $nrDiasContratoExpPro, $dtExameMedico, $dtmescompetenc, $nrsitufuncm,
                                $nrcargo, $nrescalatrabm, $idcontribuisind, $nrdependir, $nrdependsfam, $dtbaseferias, $idremuneracao, $idtppagamento, $nrestrutlegal, $nrestrutgeren, $nrtpmodalidsal, $idmultvinc, $nrfuncao, $cdcontribindividual, $nrtpmovtransfm, $dtfimcontrdetermin, 
                                $nrestrutsind, $confidencial = null,$nrorg = null,$dtRescisao = null, $dslivroadmissao = null, $dtentregaepi = null, $cdmatriculaEsocial = null, $dtvenccontrexper = null, $nrclausassecurat = null, $idpagpropfer13 = null){
        
                             
        $vinculom = $this->vinculoMestre($nrPessoa, $nrorg, $dtAdmissaoVinculo, $dtRescisao, $cdMatricula, $nrTipoVinculom, $nrVinculoEmpregaticio, $nrTipoAdmissao, $nmVinculom, $dtPrimeiraAdmissao, $dtOpcaoFGTS, $dtExameMedico, $dtAposentadoriaFGTS, $nrDiasContratoExp, $nrDiasContratoExpPro,
                                         $dslivroadmissao, $dtentregaepi, $dtvenccontrexper, $nrclausassecurat);
        
        $vinculoh = $this->vinculoHistorico($nrorg, $vinculom->getNrvinculom(), $dtmescompetenc, $nrsitufuncm, $nrcargo, $nrescalatrabm, $idcontribuisind, $nrdependir, $nrdependsfam, $dtbaseferias, $idremuneracao, $idtppagamento, $nrestrutlegal, $nrestrutgeren, $nrtpmodalidsal, $idmultvinc, 
                                            $nrfuncao, $cdcontribindividual, $nrtpmovtransfm, $dtfimcontrdetermin, $nrestrutsind, $confidencial, $cdmatriculaEsocial, $idpagpropfer13
        );
        
        return array($vinculom, $vinculoh);
        
    }
    
    public function vinculoMestre($nrpessoa, $nrorgTrab, $dtAdmissao, $dtRescisao = null, $matricula = null, $tipoVinculo = null, $nrvinculoempreg = null, $nrtpadmissao = null, $nmvinculom = null, $dtPrimeiraAdmissao = null, $dtOpcaoFGTS = null, $dtExameMedico = null, 
                                  $dtAposentadoriaFGTS = null, $nrDiasContratoExp = null, $nrDiasContratoExpPro = null, $dslivroadmissao = null, $dtentregaepi = null, $dtvenccontrexper = null, $nrclausassecurat = null){
        
        $vinculo = new $this->gpevinculom;
        
        if(empty($matricula)){
            $matricula = $vinculo->getNrvinculom();
        }
    
        $vinculo->setNrorg($nrorgTrab);
        $vinculo->setNrpessoa($nrpessoa);
        $vinculo->setNrtipovinculom($tipoVinculo);
        $vinculo->setDtadmissaovinc($dtAdmissao);
        $vinculo->setDtrescisaovinc($dtRescisao);
        $vinculo->setCdmatricula($matricula);
        $vinculo->setNrvinculoempreg($nrvinculoempreg);
        $vinculo->setNrtpadmissao($nrtpadmissao);
        $vinculo->setNmvinculom($nmvinculom);
        $vinculo->setDtprimadmissao($dtPrimeiraAdmissao);
        $vinculo->setDtopcaofgts($dtOpcaoFGTS);
        $vinculo->setDtaposentafgts($dtAposentadoriaFGTS);
        $vinculo->setNrdiascontratoexp($nrDiasContratoExp);
        $vinculo->setNrdiascontratoexppro($nrDiasContratoExpPro);
        $vinculo->setDtexamemedico($dtExameMedico);
        $vinculo->setDslivroadmissao($dslivroadmissao);
        $vinculo->setDtentregaepi($dtentregaepi);
        $vinculo->setDtvenccontrexper(DateUtil::getDataDeString($dtvenccontrexper));
        $vinculo->setNrclausassecurat($nrclausassecurat);
        
        $vinculo->setDtinclusao(DateUtil::getDataAtual());
        $vinculo->setNrorginclusao($this->nrorg);
        $vinculo->setCdoperinclusao($this->cdoperador);
        $vinculo->setDtultatu(DateUtil::getDataAtual());
        $vinculo->setNrorgultatu($this->nrorg);
        $vinculo->setCdoperultatu($this->cdoperador);
        
        $vinculo->setNrvinculom(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_VINCULOM', 1, 12, true));
        
        $this->entityManager->persist($vinculo);
        $this->entityManager->flush();
        
        return $vinculo;
        
    }
    
    public function vinculoHistorico($nrorg, $nrvinculom, $dtmescompetenc, $nrsitufuncm, $nrcargo, $nrescalatrabm, $idcontribuisind, $nrdependir, $nrdependsfam, $dtbaseferias, $idremuneracao, $idtppagamento, $nrestrutlegal, $nrestrutgeren, $nrtpmodalidsal, $idmultvinc, $nrfuncao, 
                                     $cdcontribindividual, $nrtpmovtransfm, $dtfimcontrdetermin, $nrestrutsind, $confidencial, $cdmatriculaEsocial = null, $idpagpropfer13 = null){
                                                                   
        $vinculoh = new $this->gpevinculoh;

        $vinculoh->setNrorg($nrorg);
        $vinculoh->setNrvinculom($nrvinculom);
        $vinculoh->setDtmescompetenc($dtmescompetenc);

        $vinculoh->setDtbaseferias($dtbaseferias);
        $vinculoh->setIdmultvinc($idmultvinc);
        $vinculoh->setNrsitufuncm($nrsitufuncm);
        $vinculoh->setNrtpmovtransfm($nrtpmovtransfm);
        $vinculoh->setCdcontribindividual($cdcontribindividual);
        $vinculoh->setDtfimcontrdetermin($dtfimcontrdetermin);

        $vinculoh->setNrcargo($nrcargo);
        $vinculoh->setNrfuncao($nrfuncao);
        $vinculoh->setNrescalatrabm($nrescalatrabm);
        $vinculoh->setIdremuneracao($idremuneracao);
        $vinculoh->setIdtppagamento($idtppagamento);
        $vinculoh->setNrtpmodalidsal($nrtpmodalidsal);

        $vinculoh->setNrdependir($nrdependir);
        $vinculoh->setNrdependsfam($nrdependsfam);
        $vinculoh->setConfidencial($confidencial);

        $vinculoh->setNrestrutlegal($nrestrutlegal);
        $vinculoh->setNrestrutgeren($nrestrutgeren);
        $vinculoh->setNrestrutsind($nrestrutsind);
        $vinculoh->setIdcontribuisind(($idcontribuisind) ? : 'NUNCA');
        $vinculoh->setCdmatriculaesocial($cdmatriculaEsocial);
        $vinculoh->setIdpagpropfer13($idpagpropfer13);

        $vinculoh->setDtinclusao(DateUtil::getDataAtual());
        $vinculoh->setCdoperinclusao($this->cdoperador);
        $vinculoh->setNrorginclusao($this->nrorg);
        $vinculoh->setDtultatu(DateUtil::getDataAtual());
        $vinculoh->setCdoperultatu($this->cdoperador);
        $vinculoh->setNrorgultatu($this->nrorg);

        $vinculoh->setNrvinculoh(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_VINCULOH', 1, 12, true));
        
        $this->entityManager->persist($vinculoh);
        $this->entityManager->flush();
        
        return $vinculoh;
    }
    
    public function novoEvento($nrorg, $dtinivigencia, $dtfimvigencia, $idtipoevento, $cdintegraevento, $dtmescompetenc, $idativo, $nmeventoh, $iddtocorrencia, $ideventodemonst, $dsobservacao, $idfaltasferias, $idfaltas13resc, $idgeravrzero, $idimpressevento, $idmediaevenferi, 
                               $idmediavalref, $idprocdifmovant, $idprocdifrescis, $idrepdecterc, $idrepdsr, $idrepferias, $idreprecisao, $idretrocedeprov, $idretrocedevent, $idtipoarredonda, $idtipoocorreven, $idunidrefereven, $idzeraevenfecha, $nrdigarredonda, $nreventoestorno, 
                               $nreventoneg, $nreventorescis, $nreventotransf, $nrhomologrubrica, $nrincidcp, $nrincidfgts, $nrincidirrf, $nrincidsind, $nrnaturubr, $nrordimpreseven, $nrpriorestorno, $qtlimirefereven, $qtminocorconsec, $qtminocormedfer, $vrlimitearred, $vrlimiteevento, 
                               $vrpelimitevento, $vrpercentualevento, $vrpisoevento, $vrtetoevento, $idcompsalfer, $idcompsalprov){
        
        $eventom = $this->eventoMestre($nrorg, $dtinivigencia, $dtfimvigencia, $idtipoevento);
        
        $eventoh = $this->eventoHistorico($nrorg, $eventom->getNreventom(), $cdintegraevento, $dtmescompetenc, $dtinivigencia, $idativo, $nmeventoh, $iddtocorrencia, $ideventodemonst, $dsobservacao, $idfaltasferias, $idfaltas13resc, $idgeravrzero, $idimpressevento, $idmediaevenferi, 
                                          $idmediavalref, $idprocdifmovant, $idprocdifrescis, $idrepdecterc, $idrepdsr, $idrepferias, $idreprecisao, $idretrocedeprov, $idretrocedevent, $idtipoarredonda, $idtipoocorreven, $idunidrefereven, $idzeraevenfecha, $nrdigarredonda, $nreventoestorno,
                                          $nreventoneg, $nreventorescis, $nreventotransf, $nrhomologrubrica, $nrincidcp, $nrincidfgts, $nrincidirrf, $nrincidsind, $nrnaturubr, $nrordimpreseven, $nrpriorestorno, $qtlimirefereven, $qtminocorconsec, $qtminocormedfer, $vrlimitearred,
                                          $vrlimiteevento, $vrpelimitevento, $vrpercentualevento, $vrpisoevento, $vrtetoevento, $idcompsalfer, $idcompsalprov);
    
        return array($eventom, $eventoh);
    }
    
    public function eventoMestre($nrorg, $dtinivigencia, $dtfimvigencia, $idtipoevento){
        
        $eventom = new $this->fpaeventom;
    
        $eventom->setNrorg($nrorg);
        $eventom->setDtinivigencia($dtinivigencia);
        $eventom->setDtfimvigencia($dtfimvigencia);
        $eventom->setIdtipoevento($idtipoevento);


        $eventom->setDtinclusao(DateUtil::getDataAtual());
        $eventom->setNrorginclusao($this->nrorg);
        $eventom->setCdoperinclusao($this->cdoperador);
        $eventom->setDtultatu(DateUtil::getDataAtual());
        $eventom->setNrorgultatu($this->nrorg);
        $eventom->setCdoperultatu($this->cdoperador);

        $eventom->setNreventom(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_EVENTOM', 1, 12, true));
        
        $this->entityManager->persist($eventom);
        $this->entityManager->flush();
        
        return $eventom;
    }
    
    public function eventoHistorico($nrorg, $nreventom, $cdintegraevento, $dtmescompetenc, $dtinivigencia, $idativo, $nmeventoh, $iddtocorrencia, $ideventodemonst, $dsobservacao, $idfaltasferias, $idfaltas13resc, $idgeravrzero, $idimpressevento, $idmediaevenferi, $idmediavalref, 
                                    $idprocdifmovant, $idprocdifrescis, $idrepdecterc, $idrepdsr, $idrepferias, $idreprecisao, $idretrocedeprov, $idretrocedevent, $idtipoarredonda, $idtipoocorreven, $idunidrefereven, $idzeraevenfecha, $nrdigarredonda, $nreventoestorno, $nreventoneg, 
                                    $nreventorescis, $nreventotransf, $nrhomologrubrica, $nrincidcp, $nrincidfgts, $nrincidirrf, $nrincidsind, $nrnaturubr, $nrordimpreseven, $nrpriorestorno, $qtlimirefereven, $qtminocorconsec, $qtminocormedfer, $vrlimitearred, $vrlimiteevento, 
                                    $vrpelimitevento, $vrpercentualevento, $vrpisoevento, $vrtetoevento, $idcompsalfer, $idcompsalprov){

        $eventoh = new $this->fpaeventoh;

        $eventoh->setNrorg($nrorg);
        $eventoh->setNreventom($nreventom);
        $eventoh->setCdintegraevento($cdintegraevento);
        
        $eventoh->setDtmescompetenc($dtmescompetenc);
        $eventoh->setDtinivigencia($dtinivigencia);
        $eventoh->setIdativo($idativo);
        $eventoh->setNmeventoh($nmeventoh);
        $eventoh->setIddtocorrencia($iddtocorrencia);
        $eventoh->setIdeventodemonst($ideventodemonst);
        $eventoh->setDsobservacao($dsobservacao);
        $eventoh->setIdfaltasferias($idfaltasferias);
        $eventoh->setIdfaltas13resc($idfaltas13resc);
        $eventoh->setIdgeravrzero($idgeravrzero);
        $eventoh->setIdimpressevento($idimpressevento);
        $eventoh->setIdmediaevenferi($idmediaevenferi);
        $eventoh->setIdmediavalref($idmediavalref);
        $eventoh->setIdprocdifmovant($idprocdifmovant);
        $eventoh->setIdprocdifrescis($idprocdifrescis);
        $eventoh->setIdrepdecterc($idrepdecterc);
        $eventoh->setIdrepdsr($idrepdsr);
        $eventoh->setIdrepferias($idrepferias);
        $eventoh->setIdreprecisao($idreprecisao);
        $eventoh->setIdretrocedeprov($idretrocedeprov);
        $eventoh->setIdretrocedevent($idretrocedevent);
        $eventoh->setIdtipoarredonda($idtipoarredonda);
        $eventoh->setIdtipoocorreven($idtipoocorreven);
        $eventoh->setIdunidrefereven($idunidrefereven);
        $eventoh->setIdzeraevenfecha($idzeraevenfecha);
        $eventoh->setNrdigarredonda($nrdigarredonda);
        $eventoh->setNreventoestorno($nreventoestorno);
        $eventoh->setNreventoneg($nreventoneg);
        $eventoh->setNreventorescis($nreventorescis);
        $eventoh->setNreventotransf($nreventotransf);
        $eventoh->setNrhomologrubrica($nrhomologrubrica);
        $eventoh->setNrincidcp($nrincidcp);
        $eventoh->setNrincidfgts($nrincidfgts);
        $eventoh->setNrincidirrf($nrincidirrf);
        $eventoh->setNrincidsind($nrincidsind);
        $eventoh->setNrnaturubr($nrnaturubr);
        $eventoh->setNrordimpreseven($nrordimpreseven);
        $eventoh->setNrpriorestorno($nrpriorestorno);
        $eventoh->setQtlimirefereven($qtlimirefereven);
        $eventoh->setQtminocorconsec($qtminocorconsec);
        $eventoh->setQtminocormedfer($qtminocormedfer);
        $eventoh->setVrlimitearred($vrlimitearred);
        $eventoh->setVrlimiteevento($vrlimiteevento);
        $eventoh->setVrpelimitevento($vrpelimitevento);
        $eventoh->setVrpercentualevento($vrpercentualevento);
        $eventoh->setVrpisoevento($vrpisoevento);
        $eventoh->setVrtetoevento($vrtetoevento);
        $eventoh->setIdcompsalfer($idcompsalfer);
        $eventoh->setIdcompsalprov($idcompsalprov);
    
        $eventoh->setDtinclusao(DateUtil::getDataAtual());
        $eventoh->setNrorginclusao($this->nrorg);
        $eventoh->setCdoperinclusao($this->cdoperador);
        $eventoh->setDtultatu(DateUtil::getDataAtual());
        $eventoh->setNrorgultatu($this->nrorg);
        $eventoh->setCdoperultatu($this->cdoperador);

        $eventoh->setNreventoh(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_EVENTOH', 1, 12, true));
        
        $this->entityManager->persist($eventoh);
        $this->entityManager->flush();
        
        return $eventoh;
    
    }
    
    public function formatComunicaParc($contatos, $parcnegocio){
        $arrayComunicaParc = array();
        if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('foneFixo', $contatos)){
            $telefone = array();
            $telefone['CDFORMACOMU'] = '01';
            $telefone['NRPARCNEGOCIO'] = $parcnegocio->getNrparcnegocio();
            if(strlen($contatos['foneFixo']) > 9){
                $telefone['CDPREFIXCOMUPARC'] = substr($contatos['foneFixo'], 0, 2);
                $telefone['CDCOMUNICAPARC'] = substr($contatos['foneFixo'], 2, (strlen($contatos['foneFixo'])-2));
            }else{
                $telefone['CDPREFIXCOMUPARC'] = '';
                $telefone['CDCOMUNICAPARC'] = $contatos['foneFixo'];
            }
            array_push($arrayComunicaParc, $telefone);
        }
        if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('email', $contatos)){
            $email = array();
            $email['CDFORMACOMU'] = '05';
            $email['NRPARCNEGOCIO'] = $parcnegocio->getNrparcnegocio();
            $email['CDPREFIXCOMUPARC'] = '';
            $email['CDCOMUNICAPARC'] = $contatos['email'];
            
            array_push($arrayComunicaParc, $email);
        }
        return $arrayComunicaParc;
    }

    
    
    public function novaPessoaResponsável($nrorg, $nomePessoa, $cpfPessoa, $dtmescompetenc, $parcnegocio){
        $pessoa = new $this->gpepessoa;
        
        $pessoa->setNrorg($nrorg);
        $pessoa->setNrparcnegocio($parcnegocio->getNrparcnegocio());

        $pessoa->setDtinclusao(DateUtil::getDataAtual());
        $pessoa->setNrorginclusao($this->nrorg);
        $pessoa->setCdoperinclusao($this->cdoperador);
        $pessoa->setDtultatu(DateUtil::getDataAtual());
        $pessoa->setNrorgultatu($this->nrorg);
        $pessoa->setCdoperultatu($this->cdoperador);

        $pessoa->setNrpessoa(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_PESSOA', 1, 12, true));

        $this->entityManager->persist($pessoa);
        $this->entityManager->flush();
        
        
        
        $pessoah = new $this->gpepessoah;
        
        $pessoah->setNrorg($nrorg);
        $pessoah->setNrpessoa($pessoa->getNrpessoa());
        $pessoah->setNmpessoa($nomePessoa);
        $pessoah->setNrcpfpessoa($cpfPessoa);
        $pessoah->setDtmescompetenc($dtmescompetenc);
        
        $pessoah->setDtinclusao(DateUtil::getDataAtual());
        $pessoah->setNrorginclusao($this->nrorg);
        $pessoah->setCdoperinclusao($this->cdoperador);
        $pessoah->setDtultatu(DateUtil::getDataAtual());
        $pessoah->setNrorgultatu($this->nrorg);
        $pessoah->setCdoperultatu($this->cdoperador);

        $pessoah->setNrpessoah(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_PESSOAH', 1, 12, true));
        
        $this->entityManager->persist($pessoah);
        $this->entityManager->flush();
        
        return $pessoa;
    }
    
    public function novasFormasComunica($rows) {
        foreach ($rows as $row) {
            
            $obj = new $this->comunicaParc;
            
            $obj->setNrorg($this->nrorg);
            $obj->setIdativo('S');
            $obj->setNrparcnegocio($row['NRPARCNEGOCIO']);
            $obj->setCdformacomu($row['CDFORMACOMU']);
            $obj->setCdprefixcomuparc($row['CDPREFIXCOMUPARC']);
            $obj->setCdcomunicaparc($row['CDCOMUNICAPARC']);
            $obj->setCdcomplecomuparc(null);
            $obj->setNrenderecoparc(null);
            
            $obj->setDtinclusao(DateUtil::getDataAtual());
            $obj->setCdoperinclusao($this->cdoperador);
            $obj->setNrorginclusao($this->nrorg);
            $obj->setDtultatu(DateUtil::getDataAtual());
            $obj->setCdoperultatu($this->cdoperador);
            $obj->setNrorgultatu($this->nrorg);
            
            $obj->setNrcomunicaparc(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'COMUNICAPARC', 1, 12, true));
            
            $this->entityManager->persist($obj);
            $this->entityManager->flush();
        }    
    }
    
    public function novoIntervaloHorario($nrorg, $nrhordiam, $nrseqintervhorario, $hrentrada, $hrtoleraanteentrada, $hrtolerapostentrada, $hrsaida, $hrtoleraantesaida, $hrtolerapostsaida, $hrinicionucleo = null, $hrfimnucleo = null, $iddiaocorreentrada = null, $iddiaocorresaida = null, 
                                         $idctrlmarcentrada = null, $idctrlmarcsaida = null, $idajustemarcentrada = null, $idajustemarcsaida = null, $hrprojetarintervalo = null, $idativo = null, $dsintervaloprojetado = null, $nrtpintervalo = null){
        
        $intervalohorario = new $this->gpentervaloshorario;
        
        $intervalohorario->setNrorg($nrorg);
        $intervalohorario->setNrhordiam($nrhordiam);
        $intervalohorario->setNrseqintervhorario($nrseqintervhorario);
        $intervalohorario->setHrentrada($hrentrada);
        $intervalohorario->setHrtoleraanteentrada($hrtoleraanteentrada);
        $intervalohorario->setHrtolerapostentrada($hrtolerapostentrada);
        $intervalohorario->setHrsaida($hrsaida);
        $intervalohorario->setHrtoleraantesaida($hrtoleraantesaida);
        $intervalohorario->setHrtolerapostsaida($hrtolerapostsaida);
        $intervalohorario->setHrinicionucleo($hrinicionucleo);
        $intervalohorario->setHrfimnucleo($hrfimnucleo);
        $intervalohorario->setIddiaocorreentrada($iddiaocorreentrada);
        $intervalohorario->setIddiaocorresaida($iddiaocorresaida);
        $intervalohorario->setIdctrlmarcentrada($idctrlmarcentrada);
        $intervalohorario->setIdctrlmarcsaida($idctrlmarcsaida);
        $intervalohorario->setIdajustemarcentrada($idajustemarcentrada);
        $intervalohorario->setIdajustemarcsaida($idajustemarcsaida);
        $intervalohorario->setHrprojetarintervalo($hrprojetarintervalo);
        $intervalohorario->setIdativo($idativo);
        $intervalohorario->setDsintervaloprojetado($dsintervaloprojetado);
        $intervalohorario->setNrtpintervalo($nrtpintervalo);
        
        $intervalohorario->setDtinclusao(DateUtil::getDataAtual());
        $intervalohorario->setCdoperinclusao($this->cdoperador);
        $intervalohorario->setNrorginclusao($this->nrorg);
        $intervalohorario->setDtultatu(DateUtil::getDataAtual());
        $intervalohorario->setCdoperultatu($this->cdoperador);
        $intervalohorario->setNrorgultatu($this->nrorg);
        
        $intervalohorario->setNrintervalohorario(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_INTERVALOSHORARIO', 1, 12, true));
    
        $this->entityManager->persist($intervalohorario);
        $this->entityManager->flush();
        
        return $intervalohorario;
    }

    public function novoEndereco($nrparcnegocio, $cdpais, $sgestado, $cdmunicipio, $cdlogradouro, $nmbairroendereco, $cdtipoendereco, $nrcependereco, $dscompleendereco, $nrimovelendereco, $dsendereco, $dsreferenciaende){
       
        $endereco = new $this->enderecoParc;

        $endereco->setNrorg($this->nrorg);
        $endereco->setNrparcnegocio($nrparcnegocio);
        $endereco->setCdpais($cdpais);
        $endereco->setIdativo('S');
        $endereco->setSgestado($sgestado);
        $endereco->setCdmunicipio($cdmunicipio);
        $endereco->setCdlogradouro($cdlogradouro);
        $endereco->setNmbairroendereco($nmbairroendereco);
        $endereco->setCdtipoendereco($cdtipoendereco);
        $endereco->setNrcependereco($nrcependereco);
        $endereco->setDscompleendereco($dscompleendereco);
        $endereco->setNrimovelendereco($nrimovelendereco);
        $endereco->setDsendereco($dsendereco);
        $endereco->setDsreferenciaende($dsreferenciaende);
        
        $endereco->setDtinclusao(DateUtil::getDataAtual());
        $endereco->setCdoperinclusao($this->cdoperador);
        $endereco->setNrorginclusao($this->nrorg);
        $endereco->setDtultatu(DateUtil::getDataAtual());
        $endereco->setCdoperultatu($this->cdoperador);
        $endereco->setNrorgultatu($this->nrorg);
        
        $endereco->setNrenderecoparc(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'ENDERECOPARC', 1, 10, true));
        
        $this->entityManager->persist($endereco);
        $this->entityManager->flush();
        
        return $endereco;
    }
    
    public function novoRelacionaparc($nrorg, $nrtiporelaciona, $nrparcnegocio, $dtfimrelacionamento, $nrparcnegrelac){
        
        $relacionaparc = new $this->relacionaparc;

        $relacionaparc->setNrorg($nrorg);
        $relacionaparc->setNrparcnegocio($nrparcnegocio);
        $relacionaparc->setNrtiporelaciona($nrtiporelaciona);
        $relacionaparc->setNrparcnegrelac($nrparcnegrelac);
        //$relacionaparc->setDtfimrelacionamento($dtfimrelacionamento);
        $relacionaparc->setIdativo('S');
        
        $relacionaparc->setDtinclusao(DateUtil::getDataAtual());
        $relacionaparc->setCdoperinclusao($this->cdoperador);
        $relacionaparc->setNrorginclusao($this->nrorg);
        $relacionaparc->setDtultatu(DateUtil::getDataAtual());
        $relacionaparc->setCdoperultatu($this->cdoperador);
        $relacionaparc->setNrorgultatu($this->nrorg);
        
        $relacionaparc->setNrrelacionaparc(\HCM\Util\NovoCodigo::geraCodigo($nrorg, 'RELACIONAPARC', 1, 10, true));

        $this->entityManager->persist($relacionaparc);
        $this->entityManager->flush();
        return $relacionaparc;
        
    }
    
    public function novaMovimentacao($nrorg, $nrtipotransfer, $nrvinculom, $nrestruturam, $dtinimoviment, $nrtipoestrutura = null, $nrtpmovtransf = null, $nrmotivotransf = null, $dtretroativa = null, $idatualizaacerto = 0, $dtfimmovimento = null, $dsobservacao = null){
        
        $movimentacao = new $this->gpemovimentacao;
        
        $movimentacao->setNrorg($nrorg);
        $movimentacao->setNrtipotransfer($nrtipotransfer);
        $movimentacao->setNrvinculom($nrvinculom);
        $movimentacao->setNrestruturam($nrestruturam);
        $movimentacao->setDtinimoviment($dtinimoviment);
        $movimentacao->setNrtipoestrutura($nrtipoestrutura);
        $movimentacao->setNrtpmovtransfm($nrtpmovtransf);
        $movimentacao->setNrmotivotransf($nrmotivotransf);
        $movimentacao->setDtmovimentretro($dtretroativa);
        $movimentacao->setIdatualizaacerto($idatualizaacerto);
        $movimentacao->setDtfimmoviment($dtfimmovimento);
        $movimentacao->setDsobservacao($dsobservacao);

        $movimentacao->setNrorginclusao($this->nrorg);
        $movimentacao->setDtinclusao(DateUtil::getDataAtual());
        $movimentacao->setCdoperinclusao($this->cdoperador);
        $movimentacao->setNrorgultatu($this->nrorg);
        $movimentacao->setDtultatu(DateUtil::getDataAtual());
        $movimentacao->setCdoperultatu($this->cdoperador);

        $movimentacao->setNrmovimentacao(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_MOVIMENTACAO', 1, 12, true));

        $this->entityManager->persist($movimentacao);
        $this->entityManager->flush();

        return $movimentacao;
    }
    
    public function novaAlteOcupacao($nrorg, $nrvinculom, $nrOcupacao, $dtIniOcupacao, $nrTipoOcupacao, $nrTpModalidade, $nrMotivoOcupacao = null, $nrNivelOcupacao = null, $dtFimOcupacao = null, $observacao = null){
        
        $alteOcupacao = new $this->gpealteOcupacao;

        $alteOcupacao->setNrorg($nrorg);
        $alteOcupacao->setNrvinculom($nrvinculom);
        $alteOcupacao->setNrocupacaom($nrOcupacao);
        $alteOcupacao->setDtiniocupacao($dtIniOcupacao);
        $alteOcupacao->setNrtipoocupacao($nrTipoOcupacao);
        $alteOcupacao->setNrmotivoocupa($nrMotivoOcupacao);
        $alteOcupacao->setNrnivelocupa($nrNivelOcupacao);
        $alteOcupacao->setNrtpmodalidsal($nrTpModalidade);
        $alteOcupacao->setDsobservacao($observacao);
        $alteOcupacao->setDtfimocupacao($dtFimOcupacao);

        $alteOcupacao->setDtinclusao(DateUtil::getDataAtual());
        $alteOcupacao->setCdoperinclusao($this->cdoperador);
        $alteOcupacao->setNrorginclusao($this->nrorg);
        $alteOcupacao->setDtultatu(DateUtil::getDataAtual());
        $alteOcupacao->setCdoperultatu($this->cdoperador);
        $alteOcupacao->setNrorgultatu($this->nrorg);

        $alteOcupacao->setNralteocupacao(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ALTEOCUPACAO', 1, 12, true));
        
        $this->entityManager->persist($alteOcupacao);
        $this->entityManager->flush();
        
        return $alteOcupacao;
    }
    
    public function novaAltesitufunc($nrorg, $nrvinculom, $nrSituacaoFuncional, $dtIniSituacaoFunc, $motivoAfastamento = null, $cdDiagnostico = null, $codigoCDI = null, $dtFimSituacaoFunc = null, $dtPreviretoSitu = null, $dtProrrSituacaoFunc = null,
                                     $dtVerifSituacaoFunc = null, $nrProxSituFunc = null, $qntDias = null, $dsObs = null, $nrpessoa = null){
        
        $altesitufunc = new $this->gpealtesitufunc;
        
        $altesitufunc->setNrorg($nrorg);
        $altesitufunc->setNrvinculom($nrvinculom);
        $altesitufunc->setNrsitufuncm($nrSituacaoFuncional);
        $altesitufunc->setDtinisitufunc($dtIniSituacaoFunc);
        $altesitufunc->setNrqtdiasitufunc($qntDias);

        $altesitufunc->setNrmotivoafasta($motivoAfastamento);
        $altesitufunc->setCddiagnost($cdDiagnostico);
        $altesitufunc->setCdtabecdi($codigoCDI);
        $altesitufunc->setDtfimsitufunc($dtFimSituacaoFunc);
        $altesitufunc->setDtpreviretositu($dtPreviretoSitu);
        $altesitufunc->setDtprorrsitufunc($dtProrrSituacaoFunc);
        $altesitufunc->setDtverifsitufunc($dtVerifSituacaoFunc);
        $altesitufunc->setNrproxsitufunc($nrProxSituFunc);
        $altesitufunc->setDsObsAltSitFunc($dsObs);
        $altesitufunc->setNrpessoa($nrpessoa);

        $altesitufunc->setNrorginclusao($nrorg);
        $altesitufunc->setDtinclusao(DateUtil::getDataAtual());
        $altesitufunc->setCdoperinclusao($this->cdoperador);
        $altesitufunc->setNrorgultatu($nrorg);
        $altesitufunc->setDtultatu(DateUtil::getDataAtual());
        $altesitufunc->setCdoperultatu($this->cdoperador);

        $altesitufunc->setNraltesitufunc(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ALTESITUFUNC', 1, 12, true));

        $this->entityManager->persist($altesitufunc);
        $this->entityManager->flush();
        
        return $altesitufunc;
    }
    
    public function novaAlteSalario($nrorg, $nrvinculom, $dtAlteracaoSalario, $nrOcorrencia, $nrTipoAlteracao, $vrSalario, $idTipoSalario, $nrTipoModalideSalario, $observacao = null, $vrDiferencaReal = null, $vrPercentualReal = null, $vrpercaltera = null){
        
        $alteSalario = new $this->gpealtesalario;
        
        $alteSalario->setNrorg($nrorg);
        $alteSalario->setNrvinculom($nrvinculom);
        $alteSalario->setDtaltesalario($dtAlteracaoSalario);
        $alteSalario->setNrocorrencia($nrOcorrencia);
        $alteSalario->setNrtipoaltera($nrTipoAlteracao);
        $alteSalario->setVrpercaltera($vrpercaltera);
        $alteSalario->setVrsalario($vrSalario);
        $alteSalario->setIdtpsalario($idTipoSalario);
        $alteSalario->setNrtpmodalidsal($nrTipoModalideSalario);
        $alteSalario->setDsobservacao($observacao);
        $alteSalario->setVrdiferencareal($vrDiferencaReal);
        $alteSalario->setVrpercreal($vrPercentualReal);

        $alteSalario->setDtinclusao(DateUtil::getDataAtual());
        $alteSalario->setCdoperinclusao($this->cdoperador);
        $alteSalario->setNrorginclusao($this->nrorg);
        $alteSalario->setDtultatu(DateUtil::getDataAtual());
        $alteSalario->setCdoperultatu($this->cdoperador);
        $alteSalario->setNrorgultatu($this->nrorg);
        
        
        $alteSalario->setNraltesalario(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ALTESALARIO', 1, 12, true));
        
        $this->entityManager->persist($alteSalario);
        $this->entityManager->flush();
        
        return $alteSalario;
    }
    
    public function novoIncideEvento($nrorg, $dtmescompetenc, $idincidevento, $nreventom, $nrtipoincide){
        
        $incideEvento = new $this->fpaincidevento;
    
        $incideEvento->setNrorg($nrorg);
        $incideEvento->setDtmescompetenc($dtmescompetenc);
        $incideEvento->setIdincidevento($idincidevento);
        $incideEvento->setNreventom($nreventom);
        $incideEvento->setNrtipoincide($nrtipoincide);
        
        $incideEvento->setDtinclusao(DateUtil::getDataAtual());
        $incideEvento->setNrorginclusao($this->nrorg);
        $incideEvento->setCdoperinclusao($this->cdoperador);
        $incideEvento->setDtultatu(DateUtil::getDataAtual());
        $incideEvento->setNrorgultatu($this->nrorg);
        $incideEvento->setCdoperultatu($this->cdoperador);
        
        $incideEvento->setNrincidevento(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_INCIDEVENTO', 1, 12, true));
        
        $this->entityManager->persist($incideEvento);
        $this->entityManager->flush();
        
        return $incideEvento;
    }
    
    public function novaFerias($nrorg, $nrvinculom, $dtiniaquisicao, $dtfimaquisicao, $nrtipoferias, $qtdfaltas, $qtddiasmaxferias, $qtddiasmaxabono, $qtddiasafastamento, $idcontrolferias){
        
        $ferias = new $this->fpaferias;
        
        $ferias->setNrorg($nrorg);
        $ferias->setNrvinculom($nrvinculom);
        $ferias->setDtiniaquisicao($dtiniaquisicao);
        $ferias->setDtfimaquisicao($dtfimaquisicao);
        $ferias->setNrtipoferias($nrtipoferias);
        $ferias->setQtfaltasperiodo($qtdfaltas);
        $ferias->setQtdiasmaxfe($qtddiasmaxferias);
        $ferias->setQtdiasmaxabon($qtddiasmaxabono);
        $ferias->setQtdiaafastament($qtddiasafastamento);
        $ferias->setIdcontrolferias($idcontrolferias);
        $ferias->setQtmesafastament(0);
        
        
        $ferias->setDtinclusao(DateUtil::getDataAtual());
        $ferias->setNrorginclusao($this->nrorg);
        $ferias->setCdoperinclusao($this->cdoperador);
        $ferias->setDtultatu(DateUtil::getDataAtual());
        $ferias->setNrorgultatu($this->nrorg);
        $ferias->setCdoperultatu($this->cdoperador);
        
        $ferias->setNrferias(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_FERIAS', 1, 12, true));
        
        $this->entityManager->persist($ferias);
        $this->entityManager->flush();
        
        return $ferias;
    }
    
    public function novoGozoFerias($nrorg, $nrferias, $dtinigozoferias, $dsgozoferias, $dtavisaoprevio, $dtfimgozoferias, $dtretornoferias, $idadiant13salar, $idnaopagaadic, $qtdiasabonoferi, $qtdiasferias){
    
        $gozoFerias = new $this->fpagozoferias;
        
        $gozoFerias->setNrorg($nrorg);
        $gozoFerias->setNrferias($nrferias);
        $gozoFerias->setDtinigozoferias($dtinigozoferias);
        $gozoFerias->setDsgozoferias($dsgozoferias);
        $gozoFerias->setDtavisaoprevio($dtavisaoprevio);
        $gozoFerias->setDtfimgozoferias($dtfimgozoferias);
        $gozoFerias->setDtretornoferias($dtretornoferias);
        $gozoFerias->setIdadiant13salar($idadiant13salar);
        $gozoFerias->setIdnaopagaadic($idnaopagaadic);
        $gozoFerias->setQtdiasabonoferi($qtdiasabonoferi);
        $gozoFerias->setQtdiasferias($qtdiasferias);
        
        $gozoFerias->setDtinclusao(DateUtil::getDataAtual());
        $gozoFerias->setNrorginclusao($this->nrorg);
        $gozoFerias->setCdoperinclusao($this->cdoperador);
        $gozoFerias->setDtultatu(DateUtil::getDataAtual());
        $gozoFerias->setNrorgultatu($this->nrorg);
        $gozoFerias->setCdoperultatu($this->cdoperador);
        
        $gozoFerias->setNrgozoferias(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_GOZOFERIAS', 1, 12, true));
        
        $this->entityManager->persist($gozoFerias);
        $this->entityManager->flush();
        
        return $gozoFerias;
    }
    
    public function novaEscalaTrabalho($nrorg, $dtfimvigencia, $dtinivigencia, $idativo, $nrescalatrabm, $dtmescompetenc, $nmescalatrabh, $descansosemanal, $idexigeauthoraextra, $qthrlimitesephextra, $idturnoextraferiado, $idmantempercvirada, $idatrasosoprimarc, 
                                       $idprojetaintervalo, $qthrprojetaintervalo, $iddescintervalofolga, $iddescintervaloferiado, $iddescintervalosabado, $idturnointervaloextra, $idhextranmarcinterv, $hriniperiodonoturno, $hrfimperiodonoturno, 
                                       $idgeramarcviradadia, $idadcnoturnointervalo, $idcompensaatraso, $idutapuratest, $idutapuradsr, $idnaocontrolajornada, $idgerbenfer, $qthrescalatrabh = null, $qthrsemesctrabh = null, $prientrada = null, 
                                       $prisaida = null, $segentrada = null, $segsaida = null, $nrdiasapurvales = null, $nrtpjornada = null, $nrtpintervalo = null, $nrdiainiapur = null, $nrdiafinapur = null, $idfaltasreflexo = null, $qthrsemenageren = null,
                                       $qthrescalageren = null ){
        
        
        $gpeescalatrabm = $this->escalaMestre($nrorg, $dtfimvigencia, $dtinivigencia);
        
        $gpeescalatrabh = $this->escalaHistorico($nrorg, $idativo, $gpeescalatrabm->getNrescalatrabm(), $dtmescompetenc, $nmescalatrabh, $descansosemanal, $idexigeauthoraextra, $qthrlimitesephextra, $idturnoextraferiado, $idmantempercvirada, $idatrasosoprimarc, 
                                                 $idprojetaintervalo, $qthrprojetaintervalo, $iddescintervalofolga, $iddescintervaloferiado, $iddescintervalosabado, $idturnointervaloextra, $idhextranmarcinterv, $hriniperiodonoturno, $hrfimperiodonoturno, 
                                                 $idgeramarcviradadia, $idadcnoturnointervalo, $idcompensaatraso, $idutapuratest, $idutapuradsr, $idnaocontrolajornada, $idgerbenfer, $qthrescalatrabh, $qthrsemesctrabh, $prientrada, $prisaida, $segentrada,
                                                 $segsaida, $nrdiasapurvales, $nrtpjornada, $nrtpintervalo, $nrdiainiapur, $nrdiafinapur, $idfaltasreflexo, $qthrsemenageren, $qthrescalageren);
    
        return array($gpeescalatrabm, $gpeescalatrabh);
    }
    
    public function escalaMestre($nrorg, $dtfimvigencia, $dtinivigencia){
        
        $gpeescalatrabm = new $this->gpeescalatrabm;
        
        $gpeescalatrabm->setNrorg($nrorg);
        $gpeescalatrabm->setDtfimvigencia($dtfimvigencia);
        $gpeescalatrabm->setDtinivigencia($dtinivigencia);

        $gpeescalatrabm->setDtinclusao(DateUtil::getDataAtual());
        $gpeescalatrabm->setCdoperinclusao($this->cdoperador);
        $gpeescalatrabm->setNrorginclusao($this->nrorg);
        $gpeescalatrabm->setDtultatu(DateUtil::getDataAtual());
        $gpeescalatrabm->setCdoperultatu($this->cdoperador);
        $gpeescalatrabm->setNrorgultatu($this->nrorg);
        
        
        $gpeescalatrabm->setNrescalatrabm(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ESCALATRABM', 1, 12, true));
        
        $this->entityManager->persist($gpeescalatrabm);
        $this->entityManager->flush();
        
        return $gpeescalatrabm;
    }
    
    public function escalaHistorico($nrorg, $idativo, $nrescalatrabm, $dtmescompetenc, $nmescalatrabh, $descansosemanal, $idexigeauthoraextra, $qthrlimitesephextra, $idturnoextraferiado, $idmantempercvirada, $idatrasosoprimarc, $idprojetaintervalo, 
                                    $qthrprojetaintervalo, $iddescintervalofolga, $iddescintervaloferiado, $iddescintervalosabado, $idturnointervaloextra, $idhextranmarcinterv, $hriniperiodonoturno, $hrfimperiodonoturno, $idgeramarcviradadia,
                                    $idadcnoturnointervalo, $idcompensaatraso, $idutapuratest, $idutapuradsr, $idnaocontrolajornada, $idgerbenfer, $qthrescalatrabh = null, $qthrsemesctrabh = null, $prientrada = null, $prisaida = null, $segentrada = null,
                                    $segsaida = null, $nrdiasapurvales = null, $nrtpjornada = null, $nrtpintervalo = null, $nrdiainiapur = null, $nrdiafinapur = null, $idfaltasreflexo = null, $qthrsemenageren = null, $qthrescalageren = null ){
                                        
        $gpeescalatrabh = new $this->gpeescalatrabh;
        
        $gpeescalatrabh->setNrorg($nrorg);
        $gpeescalatrabh->setIdativo($idativo);
        $gpeescalatrabh->setNrescalatrabm($nrescalatrabm);
        $gpeescalatrabh->setDescansosemanal($descansosemanal);
        $gpeescalatrabh->setDtmescompetenc($dtmescompetenc);
        $gpeescalatrabh->setHrfimperiodonoturno($hrfimperiodonoturno);
        $gpeescalatrabh->setHriniperiodonoturno($hriniperiodonoturno);
        $gpeescalatrabh->setIdadcnoturnointervalo($idadcnoturnointervalo);
        $gpeescalatrabh->setIdatrasosoprimarc($idatrasosoprimarc);
        $gpeescalatrabh->setIdcompensaatraso($idcompensaatraso);
        $gpeescalatrabh->setIddescintervaloferiado($iddescintervaloferiado);
        $gpeescalatrabh->setIddescintervalofolga($iddescintervalofolga);
        $gpeescalatrabh->setIddescintervalosabado($iddescintervalosabado);
        $gpeescalatrabh->setIdexigeauthoraextra($idexigeauthoraextra);
        $gpeescalatrabh->setIdfaltasreflexo($idfaltasreflexo);
        $gpeescalatrabh->setIdgeramarcviradadia($idgeramarcviradadia);
        $gpeescalatrabh->setIdhextranmarcinterv($idhextranmarcinterv);
        $gpeescalatrabh->setIdmantempercvirada($idmantempercvirada);
        $gpeescalatrabh->setIdnaocontrolajornada($idnaocontrolajornada);
        $gpeescalatrabh->setIdprojetaintervalo($idprojetaintervalo);
        $gpeescalatrabh->setIdturnoextraferiado($idturnoextraferiado);
        $gpeescalatrabh->setIdturnointervaloextra($idturnointervaloextra);
        $gpeescalatrabh->setIdutapuradsr($idutapuradsr);
        $gpeescalatrabh->setIdutapuratest($idutapuratest);
        $gpeescalatrabh->setNmescalatrabh($nmescalatrabh);
        $gpeescalatrabh->setNrdiafinapur($nrdiafinapur);
        $gpeescalatrabh->setNrdiainiapur($nrdiainiapur);
        $gpeescalatrabh->setNrdiasapurvales($nrdiasapurvales);
        $gpeescalatrabh->setNrtpintervalo($nrtpintervalo);
        $gpeescalatrabh->setNrtpjornada($nrtpjornada);
        $gpeescalatrabh->setPrientrada($prientrada);
        $gpeescalatrabh->setPrisaida($prisaida);
        $gpeescalatrabh->setQthrescalageren($qthrescalageren);
        $gpeescalatrabh->setQthrescalatrabh($qthrescalatrabh);
        $gpeescalatrabh->setQthrlimitesephextra($qthrlimitesephextra);
        $gpeescalatrabh->setQthrprojetaintervalo($qthrprojetaintervalo);
        $gpeescalatrabh->setQthrsemenageren($qthrsemenageren);
        $gpeescalatrabh->setQthrsemesctrabh($qthrsemesctrabh);
        $gpeescalatrabh->setSegentrada($segentrada);
        $gpeescalatrabh->setSegsaida($segsaida);
        $gpeescalatrabh->setIdgerbenfer($idgerbenfer);
        
        $gpeescalatrabh->setDtinclusao(DateUtil::getDataAtual());
        $gpeescalatrabh->setCdoperinclusao($this->cdoperador);
        $gpeescalatrabh->setNrorginclusao($this->nrorg);
        $gpeescalatrabh->setDtultatu(DateUtil::getDataAtual());
        $gpeescalatrabh->setCdoperultatu($this->cdoperador);
        $gpeescalatrabh->setNrorgultatu($this->nrorg);
        
        $gpeescalatrabh->setNrescalatrabh(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ESCALATRABH', 1, 12, true));
        
        $this->entityManager->persist($gpeescalatrabh);
        $this->entityManager->flush();
        
        return $gpeescalatrabh;
    }
    
    public function novoTurno($nrorg, $nrescalatrabm, $dtdatabase, $idativo, $dsturno){
        
        $gpeturno = new $this->gpeturno;
        
        $gpeturno->setNrorg($nrorg);
        $gpeturno->setNrescalatrabm($nrescalatrabm);
        $gpeturno->setDtdatabase($dtdatabase);
        $gpeturno->setIdativo($idativo);
        $gpeturno->setDsturno($dsturno);
        
        $gpeturno->setDtinclusao(DateUtil::getDataAtual());
        $gpeturno->setCdoperinclusao($this->cdoperador);
        $gpeturno->setNrorginclusao($this->nrorg);
        $gpeturno->setDtultatu(DateUtil::getDataAtual());
        $gpeturno->setCdoperultatu($this->cdoperador);
        $gpeturno->setNrorgultatu($this->nrorg);
        
        $gpeturno->setNrturno(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_TURNO', 1, 12, true));
        
        $this->entityManager->persist($gpeturno);
        $this->entityManager->flush();
        
        return $gpeturno;
    }
    
    public function novoHorarioDia($nrorg, $dtinivigencia, $dtfimvigencia, $dtmescompetenc, $nmhordiah, $idtipohorario, $dtesocial=null, $cdintegracao=null, $hrinicoletamarcacao=null){
        
        $gpehordiam = $this->horarioDiaMestre($nrorg, $dtinivigencia, $dtfimvigencia, $dtesocial, $cdintegracao);
        
        $gpehordiah = $this->horarioDiaHistorico($nrorg, $gpehordiam->getNrhordiam(), $dtmescompetenc, $nmhordiah, $idtipohorario, $hrinicoletamarcacao=null);
    
        return array($gpehordiam, $gpehordiah);
    }
    
    public function horarioDiaMestre($nrorg, $dtinivigencia, $dtfimvigencia, $dtesocial=null, $cdintegracao=null){
        
        $gpehordiam = new $this->gpehordiam;
        
        $gpehordiam->setNrorg($nrorg);
        $gpehordiam->setDtinivigencia($dtinivigencia);
        $gpehordiam->setDtfimvigencia($dtfimvigencia);
        $gpehordiam->setDtesocial($dtesocial);
        $gpehordiam->setCdintegracao($cdintegracao);
        
        $gpehordiam->setDtinclusao(DateUtil::getDataAtual());
        $gpehordiam->setCdoperinclusao($this->cdoperador);
        $gpehordiam->setNrorginclusao($this->nrorg);
        $gpehordiam->setDtultatu(DateUtil::getDataAtual());
        $gpehordiam->setCdoperultatu($this->cdoperador);
        $gpehordiam->setNrorgultatu($this->nrorg);
        
        $gpehordiam->setNrhordiam(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_HORDIAM', 1, 12, true));
        
        $this->entityManager->persist($gpehordiam);
        $this->entityManager->flush();
        
        return $gpehordiam;
    }
    
    public function horarioDiaHistorico($nrorg, $nrhordiam, $dtmescompetenc, $nmhordiah, $idtipohorario, $hrinicoletamarcacao=null){
        
        $gpehordiah = new $this->gpehordiah;
        
        $gpehordiah->setNrorg($nrorg);
        $gpehordiah->setNrhordiam($nrhordiam);
        $gpehordiah->setDtmescompetenc($dtmescompetenc);
        $gpehordiah->setNmhordiah($nmhordiah);
        $gpehordiah->setIdtipohorario($idtipohorario);
        $gpehordiah->setHrinicoletamarcacao($hrinicoletamarcacao); 
        
        $gpehordiah->setDtinclusao(DateUtil::getDataAtual());
        $gpehordiah->setCdoperinclusao($this->cdoperador);
        $gpehordiah->setNrorginclusao($this->nrorg);
        $gpehordiah->setDtultatu(DateUtil::getDataAtual());
        $gpehordiah->setCdoperultatu($this->cdoperador);
        $gpehordiah->setNrorgultatu($this->nrorg);
        
        $gpehordiah->setNrhordiah(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_HORDIAH', 1, 12, true));
        
        $this->entityManager->persist($gpehordiah);
        $this->entityManager->flush();
        
        return $gpehordiah;
    }
    
    public function novoTurnoHorario($nrorg, $nrturno, $nrhordiam, $nrseqhorario, $idativo, $iddiavariavel=null){
        
        $gpehorarioturno = new $this->gpehorarioturno;
        
        $gpehorarioturno->setNrorg($nrorg);
        $gpehorarioturno->setNrturno($nrturno);
        $gpehorarioturno->setNrhordiam($nrhordiam);
        $gpehorarioturno->setNrseqhorario($nrseqhorario);
        $gpehorarioturno->setIdativo($idativo);
        $gpehorarioturno->setIddiavariavel($iddiavariavel);
        
        $gpehorarioturno->setNrhorarioturno(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_HORARIOTURNO', 1, 12, true));
        
        $this->entityManager->persist($gpehorarioturno);
        $this->entityManager->flush();
        
        return $gpehorarioturno;
    }
    
    public function novoDepVinculo($nrorg, $nrpessoa, $nrtipodepende, $nrvinculom){
        
        $depvinculo = new $this->fpadepvinculo;

        $depvinculo->setNrorg($nrorg);
        $depvinculo->setNrpessoa($nrpessoa);
        $depvinculo->setNrtipodepende($nrtipodepende);
        $depvinculo->setNrvinculom($nrvinculom);

        $depvinculo->setDtinclusao(DateUtil::getDataAtual());
        $depvinculo->setNrorginclusao($this->nrorg);
        $depvinculo->setCdoperinclusao($this->cdoperador);
        $depvinculo->setDtultatu(DateUtil::getDataAtual());
        $depvinculo->setNrorgultatu($this->nrorg);
        $depvinculo->setCdoperultatu($this->cdoperador);

        $depvinculo->setNrdepvinculo(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'FPA_DEPVINCULO', 1, 12, true));
        
        $this->entityManager->persist($depvinculo);
        $this->entityManager->flush();
        
        return $depvinculo;
    }
    
    public function novaFormacao($nrorg, $nrparcnegocio, $nrestruturam, $dsinstituicao = null, $cdidioma = null, $cdstatus = null, $desareaformacaonrorg = null, $dsandamentocurso = null, $dscurso = null, $dsobservacao = null, $dtfim = null, $dtinicio = null, 
                                 $idnvidioma = null, $nrareaformacao = null, $nrcargahoraria = null, $nrcurso = null, $nrgrauconferido = null, $nrinstituicaoparc = null, $nrtipoformacao){
        
        $desFormacao = new $this->desFormacao;
        
        $desFormacao->setCdidioma($cdidioma);
        $desFormacao->setCdstatus($cdstatus);
        $desFormacao->setDesAreaformacaoNrorg($desareaformacaonrorg);
        $desFormacao->setDsandamentocurso($dsandamentocurso);
        $desFormacao->setDscurso($dscurso);
        $desFormacao->setDsinstituicao($dsinstituicao);
        $desFormacao->setDsobservacao($dsobservacao);
        $desFormacao->setDtfim($dtfim);
        $desFormacao->setDtinicio($dtinicio);
        $desFormacao->setIdnvidioma($idnvidioma);
        $desFormacao->setNrareaformacao($nrareaformacao);
        $desFormacao->setNrcargahoraria($nrcargahoraria);
        $desFormacao->setNrcurso($nrcurso);
        $desFormacao->setNrestruturam($nrestruturam);
        $desFormacao->setNrgrauconferido($nrgrauconferido);
        $desFormacao->setNrinstituicaoparc($nrinstituicaoparc);
        $desFormacao->setNrorg($nrorg);
        $desFormacao->setNrparcnegocio($nrparcnegocio);
        $desFormacao->setNrtipoformacao($nrtipoformacao);
        
        $desFormacao->setDtinclusao(DateUtil::getDataAtual());
        $desFormacao->setNrorginclusao($this->nrorg);
        $desFormacao->setCdoperinclusao($this->cdoperador);
        $desFormacao->setDtultatu(DateUtil::getDataAtual());
        $desFormacao->setNrorgultatu($this->nrorg);
        $desFormacao->setCdoperultatu($this->cdoperador);

        $desFormacao->setNrformacao(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'DES_FORMACAO', 1, 12, true));
        
        $this->entityManager->persist($desFormacao);
        $this->entityManager->flush();
        
        return $desFormacao;
    }
    
    public function novaAlteEscala($nrorg, $nrvinculom, $nrEscalaTrabalho, $dtIniEscala, $observacao = null, $dtFimEscala = null, $nrhordiam = null, $nrMotivoEscala = null, $nrturno = null, $qthrlimitesephextra = null){
        
        $alteEscala = new $this->gpealteEscala;
        
        $alteEscala->setNrorg($nrorg);
        $alteEscala->setNrvinculom($nrvinculom);
        $alteEscala->setNrescalatrabm($nrEscalaTrabalho);
        $alteEscala->setDtiniescala($dtIniEscala);
        $alteEscala->setNrmotivoescala($nrMotivoEscala);
        $alteEscala->setNrturno($nrturno);
        $alteEscala->setDtfimescala($dtFimEscala);
        $alteEscala->setNrhordiam($nrhordiam);
        $alteEscala->setDsobservacao($observacao);
        $alteEscala->setQthrlimitesephextra($qthrlimitesephextra);

        $alteEscala->setDtinclusao(DateUtil::getDataAtual());
        $alteEscala->setCdoperinclusao($this->cdoperador);
        $alteEscala->setNrorginclusao($this->nrorg);
        $alteEscala->setDtultatu(DateUtil::getDataAtual());
        $alteEscala->setCdoperultatu($this->cdoperador);
        $alteEscala->setNrorgultatu($this->nrorg);

        $alteEscala->setNralteescala(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_ALTEESCALA', 1, 12, true));
        
        $this->entityManager->persist($alteEscala);
        $this->entityManager->flush();
        
        return $alteEscala;
    }

    public function insereInstituicaoEnsino($nrorg, $instEnsino, $nrparcnegocio, $dtmescompetenc, $nrvinculom){
        $cnpjInstEnsino = \Zeedhi\Framework\Util\Functions::arrayKeyExists('cnpjInstEnsino', $instEnsino) ? $instEnsino['cnpjInstEnsino'] : null; 
        $nmRazao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('nmRazao', $instEnsino) ? $instEnsino['nmRazao'] : $cnpjInstEnsino; 
        $mensagem = '';
        
        $instituicao = $this->entityManager->getRepository(Repositories::ESTRUTURAM)->retornaEstruturaEducacional($nrorg, $dtmescompetenc, $cnpjInstEnsino, $nmRazao);
        
        if(!empty($instituicao)){
            $formacao = $this->entityManager->getRepository(Repositories::DES_FORMACAO)->retornaFormacaoPorCompetenciaEstruturaParc($nrorg, DateUtil::getUltimoDiaDoMes($dtmescompetenc), $instituicao[0]->getNrestruturam(), $nrparcnegocio, $nmRazao);
            $formacao = !empty($formacao) ? $formacao[0] : null;
            if(empty($formacao)){
                $formacao = $this->novaFormacao($nrorg, $nrparcnegocio, $instituicao[0]->getNrestruturam(), $nmRazao, null, null, null, null, null, null, null, null, null, null, null, null, null, $instituicao[0]->getNrparcnegocio(), 1);
            }    
        }else{
            $parcEnsino = $this->novoParcNegocio($nrorg, $nmRazao, $nmRazao, 'ESTRUTURA', 'N', 'N', 'LIVRE', $cnpjInstEnsino, DateUtil::getDataDeString('01/01/2020', DateUtil::FORMATO_BRASILEIRO, true), 'S', 'N');
            
            $estrutEnsino = $this->novaEstrutura(32, DateUtil::getDataDeString('01/01/2000', DateUtil::FORMATO_BRASILEIRO, true), 'S', 'N', $parcEnsino->getNrparcnegocio(), $nmRazao, $cnpjInstEnsino, null, null, null, $nmRazao, null, null, null, null, null, null, null, null,
                                                 null, null, null, $nmRazao, null, null, null, null, null, null, null, null, null, null, null, $nmRazao, $nmRazao, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                 null, null);
            $formacao = $this->novaFormacao($nrorg, $nrparcnegocio, $estrutEnsino[0]->getNrestruturam(), $nmRazao, null, null, null, null, null, null, null, null, null, null, null, null, null, $parcEnsino->getNrparcnegocio(), 1);
        }
        
        $mensagem = 'Vínculo '.$nrvinculom.': Complete o cadastro da formação (número: '.$formacao->getNrformacao().').';
        return $mensagem; 
    }
}