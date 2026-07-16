<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2206 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2206';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        $nrtipoestrutura = $this->nrtipoestrutlegal;
        
        $mensagens = array();
        
        $evtAltContratual  = (array) $this->xml->evtAltContratual;
        
        if($evtAltContratual){
            $altContratual = (array) $evtAltContratual['altContratual'];
            $ideVinculo = (array) $evtAltContratual['ideVinculo'];
            $dtAlteracao = $this->alterDateFormat($altContratual['dtAlteracao'], 2);
            $compAlteracao = DateUtil::getDataDeString($this->alterDateFormat($altContratual['dtAlteracao'], 1), DateUtil::FORMATO_BRASILEIRO, true);
            $ultDiaCompAlt = DateUtil::getDataDeString($compAlteracao->format('t/m/Y'), DateUtil::FORMATO_BRASILEIRO, true);
            
            $vinculo = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaVinculoPorMatriculaESocial($nrorg, null, $ideVinculo['matricula'], $compAlteracao, null);
            
            if($vinculo){
                // dados vínculo
                $tagVinculo = isset($altContratual['vinculo']) ? (array) $altContratual['vinculo'] : null;
                if(isset($altContratual['infoRegimeTrab'])){
                    $infoRegimeTrab = isset($altContratual['infoRegimeTrab']) ? (array) $altContratual['infoRegimeTrab'] : null;
                    $infoContrato = isset($altContratual['infoContrato']) ? (array) $altContratual['infoContrato'] : null;
                }
                if(isset($tagVinculo['infoRegimeTrab'])){
                    $infoRegimeTrab = isset($tagVinculo['infoRegimeTrab']) ? (array) $tagVinculo['infoRegimeTrab'] : null;
                    $infoContrato = isset($tagVinculo['infoContrato']) ? (array) $tagVinculo['infoContrato'] : null;
                }
                $infoCeletista = isset($infoRegimeTrab['infoCeletista']) ? (array) $infoRegimeTrab['infoCeletista'] : null;
                $remuneracao = isset($infoContrato['remuneracao']) ? (array) $infoContrato['remuneracao'] : null;
                $horario = isset($infoContrato['horContratual']) ? (array) $infoContrato['horContratual'] : null;
                $localTrabGeral = isset($infoContrato['localTrabalho']) ? (array) $infoContrato['localTrabalho']->localTrabGeral : null;
                $duracao = isset($infoContrato['duracao']) ? (array) $infoContrato['duracao'] : null;
                
                if($infoCeletista){
                    $estrutSind = \Zeedhi\Framework\Util\Functions::arrayKeyExists('cnpjSindCategProf', $infoCeletista) ? $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $infoCeletista['cnpjSindCategProf'], 10, $compAlteracao) : null;
                    $nrestrutsind = !empty($estrutSind) && $estrutSind[0]->getNrestruturam() != $vinculo->getNrestrutsind()? $estrutSind[0]->getNrestruturam() : null;
                } else {
                    $estrutSind = null;
                    $nrestrutsind = null;
                }
                
                if($localTrabGeral){
                    $estrutLegal = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $localTrabGeral['nrInsc'], $nrtipoestrutura, $compAlteracao);
                    $nrestrutlegal = !empty($estrutLegal) && $estrutLegal[0]->getNrestruturam() != $vinculo->getNrestrutlegal()? $estrutLegal[0]->getNrestruturam() : null;
                } else {
                    $estrutLegal = null;
                    $nrestrutlegal = null;
                }
                
                if($infoContrato){
                    if(isset($infoContrato['codCargo'])){
                        $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($infoContrato['codCargo'], $nrorg, $compAlteracao);
                        $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
                    } else if(isset($infoContrato['CBOCargo'])){
                        $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['CBOCargo'], $nrorg, $compAlteracao);
                        $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
                        if(is_null($nrcargo) && isset($infoContrato['nmCargo'])){
                            $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoNmocupacao($infoContrato['nmCargo'], $nrorg, $compAlteracao);
                            $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
                            if(is_null($nrcargo)){
                                //Insere Ocupação
                                $dtiniocupacao = DateUtil::getDataDeString('01/01/2000',DateUtil::FORMATO_BRASILEIRO,true);
                                $ocupacao = $this->novaOcupacao(1, $dtiniocupacao, $dtiniocupacao, $infoContrato['nmCargo'], null, null, null, null, 
                                                                   $infoContrato['CBOCargo'], null, null, null, null , null);
                                $nrcargo = $ocupacao[0]->getNrocupacaom();
                            }
                        }
                        if(is_null($nrcargo)){
                            array_push($mensagens, 'Não foi possível encontrar uma ocupação com o CBO '.$infoContrato['CBOCargo'].' nem o nome '.$infoContrato['nmCargo'].' para alteração de ocupação.');
                        }
                    } else {
                        $nrcargo = null;
                    }
                    
                    if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('codFuncao',$infoContrato)){
                        $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($infoContrato['codFuncao'], $nrorg, $compAlteracao); 
                        $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
                    } else if(isset($infoContrato['CBOFuncao'])){
                        $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['CBOFuncao'], $nrorg, $compAlteracao);
                        $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
                        if(is_null($nrfuncao) && isset($infoContrato['nmFuncao'])){
                            $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['nmFuncao'], $nrorg, $compAlteracao);
                            $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
                        }
                    } else {
                        $nrfuncao = null;
                    }
                }
                
                if($horario){
                    $escalaTrab = null;
                    $hora = !empty($horario['horario']) ? (array) $horario['horario'][0] : null;
                    
                    if($hora){
                        $escalaTrab = $this->entityManager->getRepository(Repositories::GPE_ESCALATRABM)->retornaEscalaTrabalhoPorHorario($hora['dia'], $hora['codHorContrat'], $horario['qtdHrsSem'], $horario['tpJornada'], $nrorg, $compAlteracao);
                    } else {
                        $escalaTrab = $this->entityManager->getRepository(Repositories::GPE_ESCALATRABM)->retornaEscalaTrabalhoPorQtdHrsSem($horario['qtdHrsSem'], $horario['tpJornada'], $nrorg, $compAlteracao);
                    }
                    
                    $nrEscalaTrab = !empty($escalaTrab) && $escalaTrab['nrescalatrabm'] != $vinculo->getNrescalatrabm()? $escalaTrab['nrescalatrabm'] : null;
                } else {
                    $nrEscalaTrab = null;
                }
                
                if(!is_null($nrcargo)){
                    $alteOcupacao = $this->entityManager->getRepository(Repositories::GPE_ALTEOCUPACAO)->findOneBy(
                        array('nrorg' => $nrorg, 'nrvinculom' => $vinculo->getNrvinculom(), 'dtiniocupacao' => $compAlteracao)
                    );
                    if(is_object($alteOcupacao)){
                        array_push($mensagens, 'Vínculo '.$vinculo->getNrvinculom().' já possui uma alteração de ocupação na data '.$compAlteracao.'. Favor verificar.');
                    }else{
                        $cargom = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOM)->findOneBy(array('nrorg' => $nrorg, 'nrocupacaom' => $nrcargo));
                        $alteOcupacao = $this->novaAlteOcupacao($nrorg, $vinculo->getNrvinculom(), $nrcargo, $compAlteracao, $cargom->getNrtipoocupacao(), 1, null, null, null, null);
                    }
                }else{
                    $nrcargo = $vinculo->getNrcargo();
                }
                
                if(is_null($nrfuncao)){
                    $nrfuncao = $vinculo->getNrfuncao();
                }
                
                if($nrestrutlegal){
                    if($vinculo->getNrestrutlegal()){
                        $movimLegalsaida = $this->novaMovimentacao($nrorg, 1, $vinculo->getNrvinculom(), $vinculo->getNrestrutlegal(), DateUtil::subtraiIntervalo($dtAlteracao, 1, DateUtil::DIA), $nrtipoestrutura, 9, null, null, 0, 
                                                                   DateUtil::subtraiIntervalo($dtAlteracao, 1, DateUtil::DIA), '');
                    }else{
                        array_push($mensagens, 'Vínculo '.$vinculo->getNrvinculom().' está com histórico sem estrutura legal informada. Favor verificar.');
                    }
                    $movimLegalentrada = $this->novaMovimentacao($nrorg, 1, $vinculo->getNrvinculom(), $nrestrutlegal, DateUtil::getDataDeString($dtAlteracao), $nrtipoestrutura, 8, null, null, 0, null, '');
                }else{
                    $nrestrutlegal = $vinculo->getNrestrutlegal(); 
                }
                
                $salarioAtual = $this->entityManager->getRepository(Repositories::GPE_ALTESALARIO)->retornaAlteSalarioAtual($nrorg, $vinculo->getNrvinculom(), $ultDiaCompAlt);
                if($salarioAtual){
                    if(isset($remuneracao['vrSalFx']) && $remuneracao["vrSalFx"] > $salarioAtual->getVrsalario()){
                         switch($remuneracao["undSalFixo"]){
                            case "1":
                                $idTipoSalario = 'HORA';
                                $idremuneracao = 'SAL2';
                                $idTpPagamento = 'MENSAL_SALARIO_HORA';
                                break;
                            case "2":
                                $idTipoSalario = 'DIARIO';
                                $idremuneracao = 'SAL1';
                                $idTpPagamento = 'DIARIO';
                                break;
                            case "3":
                                $idTipoSalario = 'SEMANAL';
                                $idremuneracao = 'SAL1';
                                $idTpPagamento = 'SEMANAL';
                                break;
                            case "4":
                                $idTipoSalario = 'QUINZENAL';
                                $idremuneracao = 'SAL1';
                                $idTpPagamento = 'QUINZENAL';
                                break;
                            case "5":
                                $idTipoSalario = 'MENSAL';
                                $idremuneracao = 'SAL1';
                                $idTpPagamento = 'MENSAL';
                                break;
                            case "6":
                                $idTipoSalario = null;
                                $idremuneracao = 'SAL1';
                                $idTpPagamento = 'TAREFA';
                                break;
                        }
                        $observacaoSalario = (array) $infoContrato['remuneracao'];
                        $observacaoSalario = \Zeedhi\Framework\Util\Functions::arrayKeyExists('dscSalVar', $observacaoSalario) ? $observacaoSalario['dscSalVar'] : null;
                        $nrtpmodalidsal = 1;
                        
                        $alteSalario = $this->novaAlteSalario($nrorg, $vinculo->getNrvinculom(), $compAlteracao, 1, 1, $remuneracao["vrSalFx"], $idTipoSalario, 1, $observacaoSalario, null, null, null);
                    }else{
                        $idremuneracao = $vinculo->getIdremuneracao();
                        $idTpPagamento = $vinculo->getIdtppagamento();
                        $nrtpmodalidsal = $vinculo->getNrtpmodalidsal();
                    }
                }else{
                    array_push($mensagens, 'Não foi encontrada alteração salarial para o vínculo '.$vinculo->getNrvinculom().'. Favor verificar.');
                }
                
                if($duracao){
                    $dtfimcontrdetermin = !empty($duracao['dtTerm']) ? : null;
                }else{
                    $dtfimcontrdetermin = null;
                }
                
                if($nrEscalaTrab){
                    $alteEscala = $this->entityManager->getRepository(Repositories::GPE_ALTEESCALA)->findOneBy(
                        array('nrorg' => $nrorg, 'nrvinculom' => $vinculo->getNrvinculom(), 'dtiniescala' => $compAlteracao)
                    );
                    if(is_object($alteEscala)){
                        array_push($mensagens, 'Vínculo '.$vinculo->getNrvinculom().' já possui uma alteração de escala na data '.$compAlteracao.'. Favor verificar.');
                    }else{
                        $nrturno = isset($escalaTrab['nrturno']) ? $escalaTrab['nrturno']: null;
                        $alteEscala = $this->novaAlteEscala($nrorg, $vinculo->getNrvinculom(), $nrEscalaTrab, $compAlteracao, null, null, null, null, $nrturno, null);
                    }
                }else{
                    $nrEscalaTrab = $vinculo->getNrescalatrabm();
                }
                
                if($vinculo->getDtmescompetenc() == $compAlteracao){
                    
                    // $vinculo->setDtesocial($dtAlteracao);
                    $vinculo->setNrcargo($nrcargo);
                    $vinculo->setNrescalatrabm($nrEscalaTrab);
                    $vinculo->setIdremuneracao($idremuneracao);
                    $vinculo->setIdtppagamento($idTpPagamento);
                    $vinculo->setNrestrutlegal($nrestrutlegal);
                    $vinculo->setNrtpmodalidsal($nrtpmodalidsal);
                    $vinculo->setNrfuncao($nrfuncao);
                    $vinculo->setNrestrutsind($nrestrutsind);
                    
                    $vinculo->setDtultatu(DateUtil::getDataAtual());
                    $vinculo->setCdoperultatu($this->cdoperador);
                    $vinculo->setNrorgultatu($this->nrorg);
                    
                    $this->entityManager->persist($vinculo);
                    $this->entityManager->flush();
                    
                }else{
                    $this->vinculoHistorico($nrorg, $vinculo->getNrvinculom(), $compAlteracao, $vinculo->getNrsitufuncm(), $nrcargo, $nrEscalaTrab, $vinculo->getIdcontribuisind(), $vinculo->getNrdependir(), $vinculo->getNrdependsfam(), $vinculo->getDtbaseferias(), $idremuneracao, 
                                            $idTpPagamento, $nrestrutlegal, $vinculo->getNrestrutgeren(), $nrtpmodalidsal, $vinculo->getIdmultvinc(), $nrfuncao, $vinculo->getCdcontribindividual(), $vinculo->getNrtpmovtransfm(), $vinculo->getDtfimcontrdetermin(), $nrestrutsind, 
                                            $vinculo->getConfidencial(), $vinculo->getCdmatriculaEsocial(), $vinculo->getIdpagpropfer13());
                }
                
                return array('status' => true,     
                             'messages' => [$this->msgSuccess . ' Número do vínculo atualizado: '.$vinculo->getNrvinculom()]);
            
            }else{
                return array('status' => false,     
                             'message' => "Não foi encontrado vínculo com a matrícula do esocial ".$ideVinculo['matricula']);
            }
            
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtAdmissao' no arquivo).");
        }
    }
    
}
