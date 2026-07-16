<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2299 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2299';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg       = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        
        $mensagens = array();
        
        $evtDeslig = (array) $this->xml->evtDeslig;
        
        if($evtDeslig) {
            
            //Aquisição das tags principais
            $ideEvento     = (array) $evtDeslig['ideEvento'];
            $ideEmpregador = (array) $evtDeslig['ideEmpregador'];
            $ideVinculo    = (array) $evtDeslig['ideVinculo'];
            $infoDeslig    = (array) $evtDeslig['infoDeslig'];
            
            //Dados básicos do XML do eSocial
            $matricula          = isset($ideVinculo['matricula'])    ? $ideVinculo['matricula']    : null;
            $dtDeslig           = isset($infoDeslig['dtDeslig'])     ? $infoDeslig['dtDeslig']     : null;
            $cpfTrab            = isset($ideVinculo['cpfTrab'])      ? $ideVinculo['cpfTrab']      : null;
            $mtvDeslig          = isset($infoDeslig['mtvDeslig'])    ? $infoDeslig['mtvDeslig']    : null;
            $dtProjFimAPI       = isset($infoDeslig['dtProjFimAPI']) ? $infoDeslig['dtProjFimAPI'] : null;
            $nrCertObito        = isset($infoDeslig['nrCertObito'] ) ? $infoDeslig['nrCertObito']  : null;
            $nrProcTrab         = isset($infoDeslig['nrProcTrab'] )  ? $infoDeslig['nrProcTrab']   : null;
            $indCumprParc       = isset($infoDeslig['indCumprParc']) ? $infoDeslig['indCumprParc'] : null;
            $observacao         = isset($infoDeslig['observacao'])   ? $infoDeslig['observacao']   : null;
            
            //Conversão de dados do XML diretamente para o formato do HCM
            $dtmescompetenc = DateUtil::getDataDeString($this->alterDateFormat($dtDeslig, 1), DateUtil::FORMATO_BRASILEIRO, true);
            $dtrescisaovinc = DateUtil::getDataDeString($this->alterDateFormat($dtDeslig, 2), DateUtil::FORMATO_BRASILEIRO, true);
            $dtavisoprevio  = DateUtil::getDataDeString($this->alterDateFormat($dtProjFimAPI, 2), DateUtil::FORMATO_BRASILEIRO, true);
            $nrcertobito    = $nrCertObito;
            $nrprocjud      = $nrProcTrab;
            $dsobsrescisao  = $observacao;
            
            //Aquisição do vínculo e validação do CPF da pessoa correspondente
            $objVinculoh = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaVinculoPorMatriculaESocial($nrorg, null, $matricula, $dtmescompetenc, null);
            if(empty($objVinculoh) && gettype($matricula) == 'integer') { //Testa se encontrou vinculo pela matrícula do eSocial senão tenta via nro de vínculo
                $objVinculoh = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaUltimoHistoricoCompetencia($nrorg, $matricula, $dtmescompetenc);
            }
            if(empty($objVinculoh)) { //Retorna inexistência do vínuclo se for o caso.
                return array('status'   => false,
                             'message' => "Nenhum vínculo com matrícula do eSocial ou com o número $matricula encontrado." );
            }
            $nrvinculom = $objVinculoh->getNrvinculom();
            $arrayPessoa = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $dtmescompetenc->format('d/m/Y'), $cpfTrab);
            if(isset($arrayPessoa[0]))
                $arrayPessoa = $arrayPessoa[0];
            if(empty($arrayPessoa)) { //Testa se a pessoa encontrada possui o mesmo CPF que informado no XML
                return array('status'   => false,
                             'message' => "A pessoa do vínculo nro $nrvinculom não possui um CPF cadastrado ou não é igual ao CPF informado no arquivo ($cpfTrab)." );
            }
            
            //Aquisição do tipo de demissão
            if(is_null($mtvDeslig)) {
               $nrtpdemissao = null; 
            } else {
                $params = array('nrorg'     => array($nrorgpadrao, $nrorg),
                                'cdesocial' => $mtvDeslig);
                $obj = $this->entityManager->getRepository(Repositories::FPA_TPDEMISSAO)->findOneBy($params);
                if(empty($obj)) {
                    return array('status'   => false,
                                 'message' => "Tipo de demissão ($mtvDeslig) não encontrada." );
                }
                $nrtpdemissao = $obj->getNrtpdemissao();
            }
            
            //Aquisição do tipo de aviso prévio
            if(is_null($indCumprParc) || $indCumprParc == '0') { //'0' é sem aviso prévio
                $nrtpavipre = null;
            } else {
                $params = array('nrorg'     => array($nrorgpadrao, $nrorg),
                                'cdesocial' => $indCumprParc);
                $obj = $this->entityManager->getRepository(Repositories::GPE_TIPOAVISOPRE)->findOneBy($params);
                if(empty($obj)) {
                    return array('status'   => false,
                                 'message' => "Tipo de aviso prévio ($indCumprParc) não encontrado." );
                }
                $nrtpavipre = $obj->getNrtpavipre();
            }
            
            //Atualização da tabela de vínculo e pessoa.
            try {
                //Aquisição do vinculom ($objVinculoh já adquirido acima)
                $params = array('nrorg'      => $nrorg,
                                'nrvinculom' => $nrvinculom);
                $objVinculom = $this->entityManager->getRepository(Repositories::GPE_VINCULOM)->findOneBy($params);
                
                //Aquisição da Pessoah
                $objPessoah = $this->entityManager->getRepository(Repositories::GPE_PESSOAH)->retornaHistoricoAtualPorPessoa($nrorg, $arrayPessoa['NRPESSOA'], $dtmescompetenc);
                
                //Setando os valores
                $this->entityManager->beginTransaction();
                $objVinculom->setDtrescisaovinc($dtrescisaovinc);
                $objVinculom->setDtavisoprevio($dtavisoprevio);
                $objVinculom->setNrprocjud($nrprocjud);
                $objVinculom->setDsobsrescisao($dsobsrescisao);
                $objVinculom->setNrtpdemissao($nrtpdemissao);
                $objVinculom->setNrtpavipre($nrtpavipre);
                $this->entityManager->persist($objVinculom);
                
                $objPessoah->setNrcertobito($nrcertobito);
                $this->entityManager->persist($objPessoah);
                
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