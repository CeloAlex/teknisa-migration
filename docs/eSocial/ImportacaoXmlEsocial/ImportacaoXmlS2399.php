<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2399 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2399';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg       = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        
        $mensagens = array();
        $evtTSVTermino = (array) $this->xml->evtTSVTermino;
        
        if($evtTSVTermino) {
            
            //Aquisição das tags principais
            $ideTrabSemVinculo = (array) $evtTSVTermino['ideTrabSemVinculo'];
            $infoTSVTermino    = (array) $evtTSVTermino['infoTSVTermino'];
            
            //Dados básicos do XML do eSocial
            $cpfTrab   = isset($ideTrabSemVinculo['cpfTrab'])   ? $ideTrabSemVinculo['cpfTrab']   : null;
            $nisTrab   = isset($ideTrabSemVinculo['nisTrab'])   ? $ideTrabSemVinculo['nisTrab']   : null;
            $matricula = isset($ideTrabSemVinculo['matricula']) ? $ideTrabSemVinculo['matricula'] : null;
            $codCateg  = isset($ideTrabSemVinculo['codCateg'])  ? $ideTrabSemVinculo['codCateg']  : null;
            $dtTerm    = isset($infoTSVTermino['dtTerm'])       ? $infoTSVTermino['dtTerm']       : null;

            //Conversão de dados do XML diretamente para o formato do HCM
            $dtmescompetenc = DateUtil::getDataDeString($this->alterDateFormat($dtTerm, 1), DateUtil::FORMATO_BRASILEIRO, true);
            $dtrescisaovinc = DateUtil::getDataDeString($this->alterDateFormat($dtTerm, 2), DateUtil::FORMATO_BRASILEIRO, true);

            //Aquisição da pessoa para localizar o vínculo, usando o nro do cpf
            $arrayPessoa = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $competencia, $cpfTrab);
            if(isset($arrayPessoa[0]))
                $arrayPessoa = $arrayPessoa[0];
                $nrpessoa = $arrayPessoa['NRPESSOA'];
            if(empty($arrayPessoa)) {
                return array('status'   => false,
                             'message' => "A pessoa de CPF nro $cpfTrab não foi encontrada." );
            }
            
            if($matricula){
                //Aquisição do vínculo e validação do CPF da pessoa correspondente
                $objVinculoh = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaVinculoPorMatriculaESocial($nrorg, null, $matricula, $dtmescompetenc, null);
                if(empty($objVinculoh)) { //Testa se encontrou vinculo pela matrícula do eSocial senão tenta via nro de vínculo
                    $objVinculoh = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaUltimoHistoricoCompetencia($nrorg, $matricula, $dtmescompetenc);
                }
                
                if(empty($objVinculoh)) {
                    return array('status'   => false,
                                 'message' => "Não foi encontrado nenhum vínculo para a matricula $matricula." );
                }
                
                //Aquisição do vinculom ($objVinculoh já adquirido acima)
                $params = array('nrorg'      => $nrorg,
                                'nrvinculom' => $objVinculoh->getNrvinculom());
                $objVinculom = $this->entityManager->getRepository(Repositories::GPE_VINCULOM)->findOneBy($params);
            }elseif($codCateg){
                //Aquisição do vínculo empregatício
                $params = array('cdesocial' => $codCateg);
                $objCategTrab = $this->entityManager->getRepository(Repositories::GPE_CATEGTRABESOC)->findOneBy($params);
                if(empty($objCategTrab)) {
                    return array('status'   => false,
                                 'message' => "Não foi encontrada categoria do esocial para o código $codCateg." );
                }
                
                $params = array('nrcategesoc' => $objCategTrab->getNrcategesoc());
                $objVinculoEmpreg = $this->entityManager->getRepository(Repositories::GPE_VINCULOEMPREG)->findOneBy($params);
                if(empty($objVinculoEmpreg)) {
                    return array('status'   => false,
                                 'message' => "Não foi encontrado um tipo de vínculo empregatício para a categoria ".$objCategTrab->getNrcategesoc()."-".$objCategTrab->getDscategesoc().".");
                }
                $nrvinculoempreg = $objVinculoEmpreg->getNrvinculoempreg();
                
                //Aquisicação do vínculo, busca vínculos com o número mais recente
                $params = array('nrorg'           => $nrorg,
                                'nrpessoa'        => $nrpessoa,
                                'nrvinculoempreg' => $nrvinculoempreg);
                $objVinculom = $this->entityManager->getRepository(Repositories::GPE_VINCULOM)->findOneBy($params, array('nrvinculom' => 'DESC'));
                if(empty($objVinculom)) {
                    return array('status'   => false,
                                 'message' => "Não foi encontrado nenhum vínculo para a pessoa nro $nrpessoa com vínculo empregatício nro $nrvinculoempreg." );
                }
            }
            
            //Ajustando a data de rescisão do vínculo
            try {
                //Setando os valores
                $this->entityManager->beginTransaction();
                
                $objVinculom->setDtrescisaovinc($dtrescisaovinc);
                
                $this->entityManager->persist($objVinculom);
                
                $this->entityManager->flush();
                $this->entityManager->commit();
            } catch (\Exception $e) {
                $this->entityManager->rollback();
                return array('status'   => false,
                             'message' => $e->getMessage());
            }
            
            //Retorno de sucesso
            return array('status'   => true,  
                         'messages' => $mensagens);
        } else {
            return array('status'  => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtDeslig' no arquivo).");
        }
    }
    
}