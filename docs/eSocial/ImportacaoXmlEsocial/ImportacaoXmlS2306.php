<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2306 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2306';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        
        $mensagens = array();
        
        $evtTSVAltContr = (array) $this->xml->evtTSVAltContr;
        
        if($evtTSVAltContr){
            $infoTSVAlteracao = (array) $evtTSVAltContr['infoTSVAlteracao'];
            $ideTrabSemVinculo = (array) $evtTSVAltContr['ideTrabSemVinculo'];
            $dtAlteracao = $this->alterDateFormat($infoTSVAlteracao['dtAlteracao'], 2);
            $compAlteracao = DateUtil::getDataDeString($this->alterDateFormat($infoTSVAlteracao['dtAlteracao'], 1), DateUtil::FORMATO_BRASILEIRO, true);
            
            $pessoa = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $compAlteracao->format('d/m/Y'), $ideTrabSemVinculo['cpfTrab']);
            $vinculo = !empty($pessoa) ? $this->entityManager->getRepository(Repositories::GPE_VINCULOM)->retornaVinculoAtivoPorPessoa($nrorg, $pessoa[0]['NRPESSOA'], $compAlteracao->format('d/m/Y')) : null;
            
            if($vinculo){
                // dados vínculo
                $infoComplementares = (array) $infoTSVAlteracao['infoComplementares'];
                $cargoFuncao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('cargoFuncao', $infoComplementares) ? (array) $infoComplementares['cargoFuncao'] : null; 
                $remuneracao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('remuneracao', $infoComplementares) ? (array) $infoComplementares['remuneracao'] : null;
                $infoEstagiario = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoEstagiario', $infoComplementares) ? (array) $infoComplementares['infoEstagiario'] : null; 
                $instEnsino = is_array($infoEstagiario) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('instEnsino', $infoEstagiario) ? (array) $infoEstagiario['instEnsino'] : null; 
                $ageIntegracao = is_array($infoEstagiario) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('ageIntegracao', $infoEstagiario) ? (array) $infoEstagiario['ageIntegracao'] : null;
                $nrtipovinculom = $vinculo[0]->getNrtipovinculom();
                
                
                // insere instituicão de ensino
                if($instEnsino){
                    $msg = $this->insereInstituicaoEnsino($nrorg, $instEnsino, $pessoa[0]['NRPARCNEGOCIO'], $compAlteracao, $vinculo[0]->getNrvinculom());
                    // array_push($mensagens, $msg);
                }
                // else if (empty($instEnsino) && $nrtipovinculom == "2"){
                //     array_push($mensagens, $vinculo[0]->getNrvinculom().': Não foi informada a instituição de ensino para esse vínculo.');
                // }
                
                if(!empty($cargoFuncao)){
                    if(isset($cargoFuncao['codCargo'])){
                        $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($cargoFuncao['codCargo'], $nrorg, $competencia);
                        $nrcargo = !empty($cargo) && $cargo->getNrocupacaom() != $vinculo[1]->getNrcargo() ? $cargo->getNrocupacaom() : null; 
                    } else {
                        $nrcargo = null;
                    }
                    
                    if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('codFuncao',$cargoFuncao)){
                        $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($cargoFuncao['codFuncao'], $nrorg, $compAlteracao); 
                        $nrfuncao = !empty($funcao)  && $funcao->getNrocupacaom() != $vinculo[1]->getNrfuncao() ? $funcao->getNrocupacaom() : null;
                    } else {
                        $nrfuncao = null;
                    }
                }else{
                    $nrcargo = null;
                    $nrfuncao = null;
                }
                
                if(!empty($nrcargo)){
                    $cargom = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOM)->findOneBy(array('nrorg' => $nrorg, 'nrocupacaom' => $nrcargo));
                    $alteOcupacao = $this->novaAlteOcupacao($nrorg, $vinculo[0]->getNrvinculom(), $nrcargo, DateUtil::getDataDeString($compAlteracao), $cargom->getNrtipoocupacao(), 1, null, null, null, null);
                }else{
                    $nrcargo = $vinculo[1]->getNrcargo();
                    $nrfuncao = empty($nrfuncao) ? $vinculo[1]->getNrfuncao() : $nrfuncao;
                }
                
                if(!empty($remuneracao)){
                    $vrSalario = $remuneracao['vrSalFx'];
                }else if($infoEstagiario && \Zeedhi\Framework\Util\Functions::arrayKeyExists('vlrBolsa', $infoEstagiario)){
                    $vrSalario = $infoEstagiario['vlrBolsa'];
                }else{
                    $vrSalario = null;
                }
                
                $salarioAtual = $this->entityManager->getRepository(Repositories::GPE_ALTESALARIO)->retornaAlteSalarioAtual($nrorg, $vinculo[0]->getNrvinculom(), $compAlteracao);
                // $salarioAtual = is_array($salarioAtual) && !empty($salarioAtual) ? $salarioAtual[0] : $salarioAtual;
                
                if(!empty($vrSalario) && !empty($salarioAtual) && $vrSalario > $salarioAtual->getVrsalario()){
                    if($nrtipovinculom == 2){
                        $nrvinculoempreg = 20;
                        $idTipoSalario = 'MENSAL';
                        $idremuneracao = 'ESTAGIO';
                        $nrtpmodalidsal = $vinculo[1]->getNrtpmodalidsal();
                    }else if($nrtipovinculom == 3){
                        $nrvinculoempreg = 14;
                        $idTipoSalario = 'MENSAL';
                        $idremuneracao = 'SOCIO';
                        $nrtpmodalidsal = $vinculo[1]->getNrtpmodalidsal();
                    }else if($nrtipovinculom == 10){
                        $nrvinculoempreg = 21;
                        $idTipoSalario = 'MENSAL';
                        $idremuneracao = 'AUTONOMO';
                        $nrtpmodalidsal = $vinculo[1]->getNrtpmodalidsal();
                    }else{
                        $idremuneracao = $vinculo[1]->getIdremuneracao(); 
                        $idTipoSalario = $vinculo[1]->getIdtppagamento();
                        $nrtpmodalidsal = $vinculo[1]->getNrtpmodalidsal();
                        
                    } 
                    
                    $observacaoSalario = !empty($remuneracao) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('dscSalVar', $remuneracao) ? $remuneracao['dscSalVar'] : null;
                    $alteSalario = $this->novaAlteSalario($nrorg, $vinculo[0]->getNrvinculom(), DateUtil::getDataDeString($compAlteracao), 1, 1, $vrSalario, $idTipoSalario, 1, $observacaoSalario, null, null, null);
                }else{
                    $idremuneracao = $vinculo[1]->getIdremuneracao(); 
                    $idTipoSalario = $vinculo[1]->getIdtppagamento();
                    $nrtpmodalidsal = $vinculo[1]->getNrtpmodalidsal();
                }
                
                if($vinculo[1]->getDtmescompetenc() == $compAlteracao){
                    
                    $vinculoh = $vinculo[1];
                    $vinculom = $vinculo[0];
                    
                    $vinculom->setDtesocial(DateUtil::getDataDeString($dtAlteracao, DateUtil::FORMATO_BRASILEIRO, true));
                    $vinculoh->setNrcargo($nrcargo);
                    $vinculoh->setIdremuneracao($idremuneracao);
                    $vinculoh->setIdtppagamento($idTipoSalario);
                    $vinculoh->setNrtpmodalidsal($nrtpmodalidsal);
                    $vinculoh->setNrfuncao($nrfuncao);
                    
                    $this->entityManager->persist($vinculoh);
                    $this->entityManager->flush();
                    
                }else{
                    $historicoNovo = $this->vinculoHistorico($nrorg, $vinculo[0]->getNrvinculom(), $compAlteracao, $vinculo[1]->getNrsitufuncm(), $nrcargo, $vinculo[1]->getNrescalatrabm(), $vinculo[1]->getIdcontribuisind(), $vinculo[1]->getNrdependir(), $vinculo[1]->getNrdependsfam(), 
                                                             $vinculo[1]->getDtbaseferias(), $idremuneracao, $idTipoSalario, $vinculo[1]->getNrestrutlegal(), $vinculo[1]->getNrestrutgeren(), $nrtpmodalidsal, $vinculo[1]->getIdmultvinc(), $nrfuncao, $vinculo[1]->getCdcontribindividual(), 
                                                             $vinculo[1]->getNrtpmovtransfm(), $vinculo[1]->getDtfimcontrdetermin(), $vinculo[1]->getNrestrutsind(), $vinculo[1]->getConfidencial(), $vinculo[1]->getCdmatriculaesocial(), $vinculo[1]->getIdpagpropfer13());
                }
                
                return array('status' => true,     
                             'messages' => [$this->msgSuccess . ' Número do vínculo: '.$vinculo[0]->getNrvinculom()]);
            }else{
                return array('status' => false,     
                             'message' => "Não foi encontrado vínculo com o CPF ".$ideTrabSemVinculo['cpfTrab']);
            }
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTSVAltContr' no arquivo).");
        }
    }
    
}
