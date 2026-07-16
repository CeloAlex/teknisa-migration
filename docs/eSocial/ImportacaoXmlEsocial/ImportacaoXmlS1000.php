<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1000 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1000';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml(){
        $evtInfoEmpregador = (array) $this->xml->evtInfoEmpregador;
        
        if($evtInfoEmpregador){
            $ideEmpregador = (array) $evtInfoEmpregador['ideEmpregador'];

            $operacao = $this->getOperacaoEventoCadastro($evtInfoEmpregador['infoEmpregador']);

            $infoCadastro = (array) $evtInfoEmpregador['infoEmpregador']->$operacao->infoCadastro;
            $softwareHouse = (array) $evtInfoEmpregador['infoEmpregador']->$operacao->infoCadastro->softwareHouse;
            $contato = (array) $evtInfoEmpregador['infoEmpregador']->$operacao->infoCadastro->contato;
            $idePeriodo = (array) $evtInfoEmpregador['infoEmpregador']->$operacao->idePeriodo; 

            // Utiliza as informações do XML
            if($ideEmpregador['tpInsc'] == 1){
                $idpessoafisica = 'N'; 
                $cdtipoinscricao = 'CNPJ';
            }else{
                $idpessoafisica = 'S'; 
                $cdtipoinscricao = 'CPF';
            }

            if(strlen($ideEmpregador['nrInsc']) == 8){
                //Em caso de CNPJ completa o número raiz com 0001-00 apenas para possibilitar a importação do S-1005 sem o usuário ter q completar a inscriçaõ manualmente
                $nrInsc = $ideEmpregador['nrInsc'] . '000100';
            }else{
                $nrInsc = $ideEmpregador['nrInsc'];
            }

            $estrutMesmaInsc = $this->verificaEstruturaMatrizMesmaInscricao($nrInsc, $this->nrtipoestrutlegal, $this->nrorg, $this->dtcompetencia);
            if(!empty($estrutMesmaInsc)){
                return array('status' => false, 
                             'message' => 'Foi encontrada a estrutura matriz '.$estrutMesmaInsc[0]->getNrestruturam().'-'.$estrutMesmaInsc[1]->getNmestruturah().' com o mesmo número de inscrição.');   
            }

            if(strlen($idePeriodo['iniValid']) < 10){
                $idePeriodo['iniValid'] = $this->alterDateFormat($idePeriodo['iniValid']);
            }

            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $idePeriodo) && !empty($idePeriodo['fimValid'])){
                $idePeriodo['fimValid'] = strlen($idePeriodo['fimValid']) < 10 ? $this->alterDateFormat($idePeriodo['fimValid']) : $idePeriodo['fimValid'];
            }else{
                $idePeriodo['fimValid'] = null;
            }
            $idativo = $this->retonaAtivo($idePeriodo['fimValid']);

            $nmestrutura = \Zeedhi\Framework\Util\Functions::arrayKeyExists('nmRazao', $infoCadastro) ? $infoCadastro['nmRazao'] : null;
            $nmfantasia = \Zeedhi\Framework\Util\Functions::arrayKeyExists('nmRazao', $infoCadastro) ? $infoCadastro['nmRazao'] : null;;

            $classtribut = $this->entityManager->getRepository(Repositories::CLASSTRIBUT)->findOneBy(array('cdesocial' => $infoCadastro['classTrib']));
            $cdcnae = null;
            $cdnatujuri = \Zeedhi\Framework\Util\Functions::arrayKeyExists('natJurid', $infoCadastro) ? $infoCadastro['natJurid'] : null;;

            $idoptsimples = 'N';

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
            if(isset($retorno['MatrizFilial']) && $retono['MatrizFilial'] != ""){
                if($retorno['MatrizFilial'] == "MATRIZ"){
                    $idMatriz = 'S';
                }else{
                    $idMatriz = 'N';
                }
            }
            if(isset($retorno['CodigoAtividadeEconomica']) && $retono['CodigoAtividadeEconomica'] != ""){
                $cdcnae = str_replace(array("-","/"), "", $retorno['CodigoAtividadeEconomica']);
            }
            if(isset($retorno['CodigoNaturezaJuridica']) && $retono['CodigoNaturezaJuridica'] != ""){
                $cdnatujuri = $retorno['CodigoNaturezaJuridica'];
            }

            /*["Enderecos"]=>
            array(11) {
                ["Tipo"]=> string(9) "Comercial"
                ["Logradouro"]=> string(13) "PC RIO BRANCO"
                ["Numero"]=> string(3) "100"
                ["Complemento"]=> string(17) "PAVMTO2 QUIOSQHE6"
                ["Bairro"]=> string(6) "CENTRO"
                ["Cidade"]=> string(14) "BELO HORIZONTE"
                ["Estado"]=> string(2) "MG"
                ["CEP"]=> string(8) "30111050"
                ["GeoLocalizacao"]=>
                array(2) {
                    ["Latitude"]=> string(11) "-19.9138499"
                    ["Longitude"]=> string(11) "-43.9421293"
                }
                ["DataAtualizacao"]=> string(25) "2020-04-27T00:00:00-03:00"
                ["CodigoIBGE"]=> int(3106200)
            }
            ["Email"]=> string(26) "keilaribeiro@redefc.com.br"
            ["Telefone"]=> string(10) "3134126990"*/

            // Salva Pessoa Responsável
            if(!empty($contato)){
                $pessoa = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($this->nrorg, $this->dtcompetencia, $contato['cpfCtt']);

                if(empty($pessoa)){
                    $parcnegocioPessoa = $this->novoParcNegocio($this->nrorg, $contato['nmCtt'], $contato['nmCtt'], 'PESSOA', 'S', 'N',
                                                                 'CPF', $contato['cpfCtt'], null, 'S');
                    $pessoa = $this->novaPessoaResponsável($this->nrorg, $contato['nmCtt'], $contato['cpfCtt'], DateUtil::getDataDeString($idePeriodo['iniValid'],DateUtil::FORMATO_BRASILEIRO,true), $parcnegocioPessoa);         
                    $parceiroResp = $pessoa->getNrparcnegocio();
                }else{
                    $parceiroResp = $pessoa[0]['NRPARCNEGOCIO'];
                }
            } else {
                $parceiroResp = null;
            }

            if(is_null($nmestrutura)) {
                $nmestrutura = "MATRIZ $nrInsc";
            }

            // Salva Parceiro de Negócio
            $parcnegocio = $this->novoParcNegocio($this->nrorg, $nmestrutura, $nmestrutura, 'ESTRUTURA', $idpessoafisica, 'N',
                                            $cdtipoinscricao, $nrInsc, DateUtil::getDataDeString($idePeriodo['iniValid'],DateUtil::FORMATO_BRASILEIRO,true), $idativo);

            // Salva Estrutura
            $estrutura = $this->novaEstrutura($this->nrtipoestrutlegal, $idePeriodo['iniValid'], $idativo, $idoptsimples, $parcnegocio->getNrparcnegocio(), $nmestrutura, $nrInsc, $idePeriodo['fimValid'], null, null, null, null,
                                           null, null, null, null, null, null, null, null, null, null, $nmestrutura, $cdnatujuri, $cdcnae, null, null, null, null, null, null, $parceiroResp, null, null, $nmfantasia, $nmestrutura,
                                           null, null, null, null, $classtribut->getNrclasstribut(), null, null, null, null, null, null, null, null, null, null, null, null);

            // Salva Comunicação do parceiro
            $rowsComunicaParc = $this->formatComunicaParc($contato, $parcnegocio);
            $this->novasFormasComunica($rowsComunicaParc);

            return array('status' => true,     
                         'messages' => [$this->msgSuccess . ' Estrutura criada: '.$estrutura[0]->getNrestruturam().'-'.$estrutura[1]->getNmestruturah()]);
            // return array('status' => true, 'NRESTRUTURAM' => $estrutura[0]->getNrestruturam());
            
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtInfoEmpregador' no arquivo).");
        }
    }
    
}
