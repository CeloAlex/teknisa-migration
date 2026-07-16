<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1005 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1005';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $dtcompetencia = $this->dtcompetencia;
        $nrtipoestrutura = $this->nrtipoestrutlegal;
        
        $evtTabEstab  = (array) $this->xml->evtTabEstab;
        
        if($evtTabEstab){
            $ideEmpregador = (array) $evtTabEstab['ideEmpregador'];

            $operacao = $this->getOperacaoEventoCadastro($evtTabEstab['infoEstab']);

            $ideEstab = (array) $evtTabEstab['infoEstab']->$operacao->ideEstab; 
            $dadosEstab = (array) $evtTabEstab['infoEstab']->$operacao->dadosEstab;
            $aliqGilrat = (array) $evtTabEstab['infoEstab']->$operacao->dadosEstab->aliqGilrat;

            $nrInsc = $ideEstab['nrInsc'];
            $estrutMatrizMesmaInsc = $this->verificaEstruturaMatrizMesmaInscricao($nrInsc, $nrtipoestrutura, $nrorg, $dtcompetencia);
            $estrutMesmaInsc = $this->verificaEstruturaMesmaInscricao($nrInsc, $nrtipoestrutura, $nrorg, $dtcompetencia);

            // Utiliza as informações do XML
            if($ideEstab['tpInsc'] == 1 || $ideEstab['tpInsc'] == 3 || $ideEstab['tpInsc'] == 4){
                $idpessoafisica = 'N'; 
                $cdtipoinscricao = 'CNPJ';
                if(substr($nrInsc, 8, 4) == '0001'){
                    $idMatriz = 'S';
                }else{
                    $idMatriz = 'N';
                }
            }else{
                $idMatriz = 'S';
                $idpessoafisica = 'S'; 
                $cdtipoinscricao = 'CPF';
            }

            if(strlen($ideEstab['iniValid']) < 10){
                $ideEstab['iniValid'] = $this->alterDateFormat($ideEstab['iniValid']);
            }

            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $ideEstab) && !empty($ideEstab['fimValid'])){
                $ideEstab['fimValid'] = strlen($ideEstab['fimValid']) < 10 ? $this->alterDateFormat($ideEstab['fimValid']) : $ideEstab['fimValid'];
            }else{
                $ideEstab['fimValid'] = null;
            }
            $idativo = $this->retonaAtivo($ideEstab['fimValid']);

            $cdcnae = $dadosEstab['cnaePrep'];

            $vrfap = isset($aliqGilrat['fap']) ? $aliqGilrat['fap'] : null;

            $idoptsimples = 'N';

            // Utiliza as informações do WebService substituindo as do XML caso existam
            $webservice = false;
            $retorno = array();
            $retorno = $this->consultaDadoRF($nrInsc);
            if($retorno['Status'] == true){
                $webservice = true;
            }
            if(isset($retorno['CodigoAtividadeEconomica']) && $retorno['CodigoAtividadeEconomica'] != ""){
                $cdcnae = str_replace(array("-","/"), "", $retorno['CodigoAtividadeEconomica']);
            }

            if($idMatriz == 'S'){
                if(empty($estrutMatrizMesmaInsc)){
                    return array('status' => false, 
                                 'message' => 'Não foi encontrado o registro a estrutura matriz de CNPJ '.$nrInsc.' para ser atualizado.');   
                }else{
                    $estrutura = $estrutMatrizMesmaInsc;
                    $estruturah = $estrutMatrizMesmaInsc[1];

                    //Verifica se a inscrição é a matriz é o mesmo cnpj raiz e se possui o final 00 importado no S-1000 para atualizar com o cnpj completo do S-1005
                    if(substr($estruturah->getCdcnpjestrut(),0,12) == substr($nrInsc,0,12) && substr($estruturah->getCdcnpjestrut(),8,6) == '000100'){
                        $estruturah->setCdcnpjestrut($nrInsc);
                    }

                    //Completa o cadastro da matriz com os dados do S-1005
                    $estruturah->setCdcnae($cdcnae);
                    $estruturah->setVrfap($vrfap);
                    $estruturah->setDtultatu(DateUtil::getDataAtual());
                    $estruturah->setCdoperultatu($this->cdoperador);
                    $estruturah->setNrorgultatu($this->nrorg);

                    $this->entityManager->persist($estruturah);
                    $this->entityManager->flush();

                    return array('status' => true, 
                                 'messages' => [$this->msgSuccess . ' Cadastro da estrutura ' . $estrutMatrizMesmaInsc[0]->getNrestruturam().'-'.$estrutMatrizMesmaInsc[1]->getNmestruturah() . ' foi atualizado.']);   
                }
            }else{
                if(!empty($estrutMesmaInsc)){
                    return array('status' => false, 
                                 'message' => 'Já foi localizada a estrutura '.$estrutMesmaInsc[0]->getNrestruturam().'-'.$estrutMesmaInsc[1]->getNmestruturah().' para essa filial .');
                }

                $estrututaMatriz = current($this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaMatrizPorFilial($nrorg, $ideEmpregador['nrInsc'], $nrtipoestrutura, $dtcompetencia));
                if(empty($estrututaMatriz)){
                    return array('status' => false, 
                                 'message' => 'Não foi encontrada no sistema nenhuma estrutura matriz para essa filial.'); 
                }

                if($ideEstab['tpInsc'] == 3){
                    $cdceiestrut = null;
                    $cdcaepfestrut = $nrInsc; 
                    $cdcnpjestrut = $estrututaMatriz['CDCNPJESTRUT'];
                }else if($ideEstab['tpInsc'] == 4){
                    $cdceiestrut = $nrInsc;
                    $cdcaepfestrut = null; 
                    $cdcnpjestrut = $estrututaMatriz['CDCNPJESTRUT'];
                }else{
                    $cdceiestrut = null;
                    $cdcaepfestrut = null; 
                    $cdcnpjestrut = $nrInsc;
                }

                $nmestrutura = $this->montaNomeEstrutura($estrututaMatriz['NMRAZSOCESTRUT'], $nrInsc, 'FILIAL');
                $nmfantasia = $nmestrutura;
                $cdnatujuri = null;

                // Utiliza as informações do WebService substituindo as do XML caso existam
                if($retorno){
                    if(isset($retorno['RazaoSocial']) && $retorno['RazaoSocial'] != ""){
                        $nmestrutura = $retorno['RazaoSocial'];
                    }
                    if(isset($retorno['NomeFantasia']) && $retorno['NomeFantasia'] != ""){
                        $nmfantasia = $retorno['NomeFantasia'];
                    }
                    if(isset($retorno['DataFundacao']) && $retorno['DataFundacao'] != ""){
                        $iniValid = $retorno['DataFundacao'];
                    }
                    if(isset($retorno['CodigoNaturezaJuridica']) && $retorno['CodigoNaturezaJuridica'] != ""){
                        $cdnatujuri = $retorno['CodigoNaturezaJuridica'];
                    }
                }

                // Salva Parceiro de Negócio
                $parcnegocio = $this->novoParcNegocio($nrorg, $nmestrutura, $nmestrutura, 'ESTRUTURA', $idpessoafisica, 'N',
                                                      $cdtipoinscricao, $nrInsc, DateUtil::getDataDeString($ideEstab['iniValid'],DateUtil::FORMATO_BRASILEIRO,true), $idativo);

                // Salva Estrutura
                $estrutura = $this->novaEstrutura($this->nrtipoestrutlegal, $ideEstab['iniValid'], $idativo, $idoptsimples, $parcnegocio->getNrparcnegocio(), $nmestrutura, $cdcnpjestrut, $ideEstab['fimValid'], null, null, null, null,
                                                  null, null, null, null, null, null, null, null, null, $cdceiestrut, $nmestrutura, $cdnatujuri, $cdcnae, null, null, null, null, null, null, null, null, null, $nmfantasia, $nmestrutura,
                                                  null, null, null, null, null, $vrfap, null, null, null, null, null, null, null, null, null, $cdcaepfestrut, null);
            }

            return array('status' => true,     
                         'messages' => [$this->msgSuccess . ' Estrutura criada : '.$estrutura[0]->getNrestruturam().'-'.$estrutura[1]->getNmestruturah()]);

            // return array('status' => true, 'NRESTRUTURAM' => $estrutura[0]->getNrestruturam());
            
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTabEstab' no arquivo).");
        }
    }
    
}
