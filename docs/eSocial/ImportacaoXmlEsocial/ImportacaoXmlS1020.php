<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1020 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1020';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $dtcompetencia = $this->dtcompetencia;
        $nrtipoestruturalegal = $this->nrtipoestrutlegal;
        
        $evtTabLotacao  = (array) $this->xml->evtTabLotacao;
        
        if($evtTabLotacao){
            $ideEmpregador = (array) $evtTabLotacao['ideEmpregador'];
            
            $operacao = $this->getOperacaoEventoCadastro($evtTabLotacao['infoLotacao']);
            
            $ideLotacao = (array) $evtTabLotacao['infoLotacao']->$operacao->ideLotacao; 
            $dadosLotacao = (array) $evtTabLotacao['infoLotacao']->$operacao->dadosLotacao;
            $fpasLotacao = (array) $evtTabLotacao['infoLotacao']->$operacao->dadosLotacao->fpasLotacao;
            
            $tplotatribut = $this->entityManager->getRepository(Repositories::ESO_TPLOTATRIBUT)->findOneBy(array('cdesocial' => $dadosLotacao['tpLotacao']));
            if(empty($tplotatribut)){
                return array('status' => false, 
                             'message' => 'Não foi encontrado o tipo de lotação informado ('.$dadosLotacao['tpLotacao'].')');
            }
            
            $tipoestruturaLotacao = $this->entityManager->getRepository(Repositories::TIPOESTRUTURA)->findBy(array('nrtplotatribut' => $tplotatribut->getNrtplotatribut(), 'nrorg' => array($nrorg, $this->nrorgpadrao)));
            if(empty($tipoestruturaLotacao)){
                return array('status' => false, 
                             'message' => 'Não foi encontrado tipo de estrutura para o tipo de lotação informado. ('.$dadosLotacao['tpLotacao'].')');
            }
            
            $nrtipoestrutura = $this->retonarTipoEstruturaInserida($tipoestruturaLotacao);
            if(empty($nrtipoestrutura)){
                return array('status' => false, 
                             'message' => 'Não foi encontrado tipo de estrutura legal nem tomador para o tipo de lotação informado. ('.$dadosLotacao['tpLotacao'].')');
            }
            
            if(isset($dadosLotacao['nrInsc'])){
                $nrInsc = $dadosLotacao['nrInsc'];
                $estrutMesmaInsc = $this->verificaEstruturaMesmaInscricao($nrInsc, $nrtipoestrutura['numero'], $nrorg, $dtcompetencia);
            } else {
                $nrInsc = $ideEmpregador['nrInsc'];
                $estrutMesmaInsc = $this->verificaEstruturaMatrizMesmaInscricao($nrInsc, $nrtipoestrutura['numero'], $nrorg, $dtcompetencia);
            }
            
            // Utiliza as informações do XML
            if($nrtipoestrutura['tipo'] == 'LEGAL'){
                $idTomador = 'N';
            }else{
                $idTomador = 'S';
            }
            
            if(strlen($nrInsc) == 14){
                $idpessoafisica = 'N'; 
                $cdtipoinscricao = 'CNPJ';
            }else{
                $idpessoafisica = 'S'; 
                $cdtipoinscricao = 'CPF';
            }
            
            if(strlen($ideLotacao['iniValid']) < 10){
                $ideLotacao['iniValid'] = $this->alterDateFormat($ideLotacao['iniValid']);
            }
            
            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $ideLotacao) && !empty($ideLotacao['fimValid'])){
                $ideLotacao['fimValid'] = strlen($ideLotacao['fimValid']) < 10 ? $this->alterDateFormat($ideLotacao['fimValid']) : $ideLotacao['fimValid'];
            }else{
                $ideLotacao['fimValid'] = null;
            }
            
            $idativo = $this->retonaAtivo($ideLotacao['fimValid']);
            
            $idoptsimples = 'S';
            
            if($idTomador == 'N'){
                if(empty($estrutMesmaInsc)){
                    return array('status' => false, 
                                 'message' => 'Não foi encontrado o registro da estrutura matriz de CNPJ '.$nrInsc.' para ser atualizado.');   
                }else{
                    $estrutura = $estrutMesmaInsc;
                    $estruturah = $estrutMesmaInsc[1];
                    
                    $estruturah->setCdterceiro($fpasLotacao['codTercs']);
                    $estruturah->setCdfpas($fpasLotacao['fpas']);
                    $estruturah->setDtultatu(DateUtil::getDataAtual());
                    $estruturah->setCdoperultatu($this->cdoperador);
                    $estruturah->setNrorgultatu($this->nrorg);
                    
                    $this->entityManager->persist($estruturah);
                    $this->entityManager->flush();
                    
                    return array('status' => true, 
                                 'messages' => [$this->msgSuccess . ' Cadastro da estrutura ' . $estrutMesmaInsc[0]->getNrestruturam().'-'.$estrutMesmaInsc[1]->getNmestruturah() . ' foi atualizado.']);   
                }
            }else{
                if(!empty($estrutMesmaInsc)){
                   return array('status' => false, 
                                 'message' => 'Já foi localizado o registro de número '.$estrutMesmaInsc[0]->getNrestruturam().'-'.$estrutMesmaInsc[1]->getNmestruturah().' para essa lotação.');    
                }
                
                $nmestrutura = $this->montaNomeEstrutura('', $nrInsc, 'TOMADOR');
                $nmfantasia = $nmestrutura;
                $cdcnae = null;
                $cdnatujuri = null;
                
                // Utiliza as informações do WebService substituindo as do XML caso existam
                $webservice = false;
                $retorno = array();
                $retorno = $this->consultaDadoRF($nrInsc);
                if($retorno['Status'] == true){
                    $webservice = true;
                }
                if(isset($retorno['RazaoSocial']) && $retono['RazaoSocial'] != ""){
                    $nmestrutura = $retorno['RazaoSocial'];
                }
                if(isset($retorno['NomeFantasia']) && $retono['NomeFantasia'] != ""){
                    $nmfantasia = $retorno['NomeFantasia'];
                }
                if(isset($retorno['DataFundacao']) && $retono['DataFundacao'] != ""){
                    $iniValid = $retorno['DataFundacao'];
                }
                if(isset($retorno['CodigoAtividadeEconomica']) && $retono['CodigoAtividadeEconomica'] != ""){
                    $cdcnae = str_replace(array("-","/"), "", $retorno['CodigoAtividadeEconomica']);
                }
                if(isset($retorno['CodigoNaturezaJuridica']) && $retono['CodigoNaturezaJuridica'] != ""){
                    $cdnatujuri = $retorno['CodigoNaturezaJuridica'];
                }
                
                // Salva Parceiro de Negócio
                $parcnegocio = $this->novoParcNegocio($nrorg, $nmestrutura, $nmestrutura, 'ESTRUTURA', $idpessoafisica, 'N',
                                                      $cdtipoinscricao, $nrInsc, DateUtil::getDataDeString($ideLotacao['iniValid'],DateUtil::FORMATO_BRASILEIRO,true), $idativo);
                
                // Salva Estrutura
                $estrutura = $this->novaEstrutura($nrtipoestrutura['numero'], $ideLotacao['iniValid'], $idativo, $idoptsimples, $parcnegocio->getNrparcnegocio(), $nmestrutura, $nrInsc, $ideLotacao['fimValid'], $ideLotacao['codLotacao'], null, null, null,
                                                  null, null, null, null, null, null, null, null, null, null, $nmestrutura, $cdnatujuri, $cdcnae, null, null, null, null, null, null, null, $fpasLotacao['fpas'], null, $nmfantasia, $nmestrutura,
                                                  null, null, null, $fpasLotacao['codTercs'], null, null, null, null, null, null, null, null, null, null, null, null, null);
            
                return array('status' => true,     
                             'messages' => [$this->msgSuccess . ' Número da estrutura criada: '.$estrutura[0]->getNrestruturam()]);
            }
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTabLotacao' no arquivo).");
        }
    }
    
}
