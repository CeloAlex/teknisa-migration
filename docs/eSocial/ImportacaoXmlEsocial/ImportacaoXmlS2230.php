<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2230 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2230';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        $dataAtual = DateUtil::getDataAtual();
        
        $mensagens = array();
        
        $evtAfastTemp  = (array) $this->xml->evtAfastTemp;
        
        if($evtAfastTemp){
            $ideVinculo = (array) $evtAfastTemp['ideVinculo'];
            $infoAfastamento = (array) $evtAfastTemp['infoAfastamento'];
            $iniAfastamento = \Zeedhi\Framework\Util\Functions::arrayKeyExists('iniAfastamento', $infoAfastamento) ? (array) $infoAfastamento['iniAfastamento'] : null;
            $infoRetif = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoRetif', $infoAfastamento) ? (array) $infoAfastamento['infoRetif'] : null;
            $fimAfastamento = \Zeedhi\Framework\Util\Functions::arrayKeyExists('fimAfastamento', $infoAfastamento) ? (array) $infoAfastamento['fimAfastamento'] : null;
            $infoAtestado = !empty($iniAfastamento) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoAtestado', $iniAfastamento) ? (array) $iniAfastamento['infoAtestado'] : null;
            $emitente = !empty($infoAtestado) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('emitente', $infoAtestado) ? (array) $infoAtestado['emitente'] : null;
            $infoCessao = !empty($iniAfastamento) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoCessao', $iniAfastamento) ? (array) $iniAfastamento['infoCessao'] : null;
            $infoMandSind = !empty($iniAfastamento) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoMandSind', $iniAfastamento) ? (array) $iniAfastamento['infoMandSind'] : null;
            
            $dadosVinculo = '';
            if(!\Zeedhi\Framework\Util\Functions::arrayKeyExists('matricula', $ideVinculo) || is_object($ideVinculo['matricula'])){
                $matricula = null;
            }else{
                $matricula =  $ideVinculo['matricula'];
                $dadosVinculo .= 'matrícula esocial: '.$ideVinculo['matricula'].' | ';
            }
            if(!\Zeedhi\Framework\Util\Functions::arrayKeyExists('codCateg', $ideVinculo) || is_object($ideVinculo['codCateg'])){
                $categoria = null;
            }else{
                $categoria =  $ideVinculo['codCateg'];
                $dadosVinculo .= 'cdesocial da categoria: '.$ideVinculo['codCateg'].' | ';
            }
            if(!\Zeedhi\Framework\Util\Functions::arrayKeyExists('cpfTrab', $ideVinculo) || is_object($ideVinculo['cpfTrab'])){
                $cfppessoa = null;
            }else{
                $cfppessoa =  $ideVinculo['cpfTrab'];
                $dadosVinculo .= 'CPF: '.$ideVinculo['cpfTrab'];
            }
            
            $vinculo = $this->entityManager->getRepository(Repositories::GPE_VINCULOM)->retornaVinculoPorCPF($nrorg, $cfppessoa, $matricula, $competencia, $categoria, 'N');
            
            if(!empty($vinculo)){
                if($iniAfastamento['codMotAfast'] == 15){
                    $dtadmissao = $vinculo[0]->getDtadmissaovinc();
                    $dtbaseferias = $vinculo[1]->getDtbaseferias();
                    $inicio = empty($dtbaseferias) ? DateUtil::truncateData($dtbaseferias) : DateUtil::truncateData($dtadmissao);
                    $fim = DateUtil::truncateData(DateUtil::adicionaIntervalo(DateUtil::subtraiIntervalo($inicio, 1, DateUtil::DIA), 1, DateUtil::ANO));
                    
                    $feriasAfastamento = null;
                    while(strtotime($inicio->format('Y-m-d')) < strtotime($dataAtual->format('Y-m-d'))){
                        $ferias = $this->entityManager->getRepository(Repositories::FPA_FERIAS)->findOneBy(array('nrorg' => $nrorg, 'nrvinculom' => $vinculo[0]->getNrvinculom(), 'dtiniaquisicao' => $inicio, 'dtfimaquisicao' => $fim));
                        
                        if(empty($ferias)){
                            if($vinculo[0]->getNrtipovinculom() == 2){
                                $nrtipoferias = 2;
                            }else{
                                $nrtipoferias = 1;
                            }
                            $qtdfaltas = 0;
                            $qtddiasmaxferias = 30;
                            $qtddiasmaxabono = 0;
                            $qtddiasafastamento = 0;
                            $idcontrolferias = 'ABERTO';
                            
                            // insere ferias para vínculo
                            $ferias = $this->novaFerias($nrorg, $vinculo[0]->getNrvinculom(), $inicio, $fim, $nrtipoferias, $qtdfaltas, $qtddiasmaxferias, $qtddiasmaxabono, $qtddiasafastamento, $idcontrolferias);
                        }
                        
                        $inicio = DateUtil::truncateData(DateUtil::adicionaIntervalo($fim, 1, DateUtil::DIA));
                        $fim = DateUtil::truncateData(DateUtil::adicionaIntervalo(DateUtil::subtraiIntervalo($inicio, 1, DateUtil::DIA), 1, DateUtil::ANO));
                        
                        if(strtotime($iniAfastamento['dtIniAfast']) >= strtotime($inicio->format('Y-m-d')) && strtotime($iniAfastamento['dtIniAfast']) <= strtotime($fim->format('Y-m-d'))){
                            $feriasAfastamento = $ferias;
                        }
                        
                    }
                    array_push($mensagens, "Os registros de férias entre ".(empty($dtbaseferias) ? $dtbaseferias->format('d/m/Y') : $dtadmissao->format('d/m/Y'))." e ".$fim->format('d/m/Y')." foram incluídos para o vínculo ".$vinculo[0]->getNrvinculom().".");
                    
                    if($feriasAfastamento){
                        $gozoFerias = $this->entityManager->getRepository(Repositories::FPA_GOZOFERIAS)->findBy(array('nrorg' => $nrorg, 'nrferias' => $feriasAfastamento->getNrferias()));
                        $qtdias = 0;
                        
                        $dtinigozoferias = DateUtil::getDataDeString($this->alterDateFormat($iniAfastamento['dtIniAfast'], 2), DateUtil::FORMATO_BRASILEIRO, true);
                        $dtfimgozoferias = DateUtil::getDataDeString($this->alterDateFormat($fimAfastamento['dtTermAfast'], 2), DateUtil::FORMATO_BRASILEIRO, true);
                        if($dtfimgozoferias){
                            $dtretornoferias = DateUtil::adicionaIntervalo($dtfimgozoferias, 1, DateUtil::DIA);
                            $qtdiasferias = $this->retornaQtDias($dtinigozoferias, $dtfimgozoferias);
                        }else{
                            $dtretornoferias = null;
                            $qtdiasferias = false;
                        }
                        $idadiant13salar = "N";
                        $idnaopagaadic = "N";
                        
                        if($gozoFerias){
                            foreach($gozoFerias as $gozo){
                                if($gozo->getDtfimgozoferias()){
                                    if($dtinigozoferias && $dtfimgozoferias){
                                        if((DateUtil::getIntervaloEmSegundos($dtinigozoferias,$gozo->getDtinigozoferias()) <= 0 && DateUtil::getIntervaloEmSegundos($dtinigozoferias,$gozo->getDtfimgozoferias()) >= 0) ||
                                           (DateUtil::getIntervaloEmSegundos($dtfimgozoferias,$gozo->getDtinigozoferias()) <= 0 && DateUtil::getIntervaloEmSegundos($dtfimgozoferias,$gozo->getDtfimgozoferias()) >= 0)){
                                            return array('status' => false,     
                                             'message' => "Já existe um gozo de férias para o vínculo ".$vinculo[0]->getNrvinculom()." com o período ".$gozo->getDtinigozoferias()->format('d/m/Y')." a ".$gozo->getDtfimgozoferias()->format('d/m/Y').".");
                                        }
                                    }else if($dtinigozoferias){
                                        if(DateUtil::getIntervaloEmSegundos($dtinigozoferias,$gozo->getDtinigozoferias()) <= 0 && DateUtil::getIntervaloEmSegundos($dtinigozoferias,$gozo->getDtfimgozoferias()) >= 0){
                                            return array('status' => false,     
                                             'message' => "Já existe um gozo de férias para o vínculo ".$vinculo[0]->getNrvinculom()." com o período ".$gozo->getDtinigozoferias()->format('d/m/Y')." a ".$gozo->getDtfimgozoferias()->format('d/m/Y').".");
                                        }
                                    }else if($dtfimgozoferias){
                                        if((DateUtil::getIntervaloEmSegundos($dtfimgozoferias,$gozo->getDtinigozoferias()) <= 0 && DateUtil::getIntervaloEmSegundos($dtfimgozoferias,$gozo->getDtfimgozoferias()) >= 0)){
                                            return array('status' => false,     
                                             'message' => "Já existe um gozo de férias para o vínculo ".$vinculo[0]->getNrvinculom()." com o período ".$gozo->getDtinigozoferias()->format('d/m/Y')." a ".$gozo->getDtfimgozoferias()->format('d/m/Y').".");
                                        }
                                    }
                                }else{
                                    if(DateUtil::getIntervaloEmSegundos($dtinigozoferias,$gozo->getDtinigozoferias()) == 0){
                                        return array('status' => false,     
                                         'message' => "Já existe um gozo de férias para o vínculo ".$vinculo[0]->getNrvinculom()." com o início ".$gozo->getDtinigozoferias()->format('d/m/Y').".");
                                    }
                                }
                                
                                if($gozo->getQtdiasferias()){
                                    $qtdias += empty($gozo->getQtdiasferias()) ? 0 : $gozo->getQtdiasferias();
                                }else{
                                    if($gozo->getDtfimgozoferias()){
                                        $qtdias += $this->retornaQtDias($gozo->getDtinigozoferias(), $gozo->getDtfimgozoferias());
                                    }
                                }
                            }
                        }
                            
                        // insere gozo de ferias 
                        $gozo = $this->novoGozoFerias($nrorg, $feriasAfastamento->getNrferias(), $dtinigozoferias, null, null, $dtfimgozoferias, $dtretornoferias, $idadiant13salar, $idnaopagaadic, null, $qtdiasferias);
                        array_push($mensagens, "Foi incluído um gozo de férias para o vínculo ".$vinculo[0]->getNrvinculom()." com código ".$gozo->getNrgozoferias().".");
                        
                        if(($qtdias + $qtdiasferias) == 30){
                            // altera idcontrolaferias
                            $feriasAfastamento->setIdcontrolferias('GOZADO_INTEGRAL');
                            
                            $this->entityManager->persist($feriasAfastamento);
                            $this->entityManager->flush();
                        }else if(($qtdias + $qtdiasferias) < 30){
                            // altera idcontrolaferias
                            $feriasAfastamento->setIdcontrolferias('GOZADO_PARCIAL');
                            
                            $this->entityManager->persist($feriasAfastamento);
                            $this->entityManager->flush();
                        }else{
                            array_push($mensagens, "A soma de dias de férias ultrapassou o limite de 30 dias do vínculo ".$vinculo[0]->getNrvinculom().". Número das férias: ".$feriasAfastamento->getNrferias().".");
                        }
                    }else{
                        return array('status' => false,     
                                     'message' => "Não foi possível incluir ou encontrar período de ferias referente a esse gozo de férias (".$inicio->format('d/m/Y').") para o vínculo ".$vinculo[0]->getNrvinculom());
                    }
                }else{
                    $altesitufunc = $this->entityManager->getRepository(Repositories::GPE_ALTESITUFUNC)->retornaSituacaoFuncionalImportacao($nrorg, $vinculo[0]->getNrvinculom(), 2);
                    
                    if(empty($altesitufunc)){
                        return array('status' => false,     
                                     'message' => "Não foi encontrada nenhuma situação funcional cadastrada para o vínculo ".$vinculo[0]->getNrvinculom());
                    }else{
                        $altesitufunc = is_array($altesitufunc) ? $altesitufunc : [$altesitufunc];
                    }
                    
                    $dtIniAfast = $iniAfastamento && \Zeedhi\Framework\Util\Functions::arrayKeyExists('dtIniAfast', $iniAfastamento) ? $iniAfastamento['dtIniAfast'] : null; 
                    $dtTermAfast = $fimAfastamento && \Zeedhi\Framework\Util\Functions::arrayKeyExists('dtTermAfast', $fimAfastamento) ? $fimAfastamento['dtTermAfast'] : null; 
                    
                    $alteSituAnte = null;
                    $alteSituPos = null;
                    $situRepetida = false;
                    $dtAfastamento = !empty($dtIniAfast) ? $dtIniAfast : $dtTermAfast; 
                    $idInsereFim = empty($dtIniAfast) ? true : false; 
                        
                    // foreach($altesitufunc as $index => $alteracao){
                    //     $inialtesitu = strtotime($alteracao->getDtinisitufunc()->format('Y-m-d')); 
                    //     $inialteprox = \Zeedhi\Framework\Util\Functions::arrayKeyExists($index+1, $altesitufunc) ? strtotime($altesitufunc[$index+1]->getDtinisitufunc()->format('Y-m-d')) : 0;
                        
                        
                    //     if($inialtesitu == strtotime($dtAfastamento) && !$idInsereFim){
                    //         $situRepetida = true;
                    //     }else if(($inialtesitu < strtotime($dtAfastamento) || ($inialtesitu == strtotime($dtAfastamento) && $idInsereFim))  && (($inialteprox > strtotime($dtAfastamento)) || $inialteprox == 0)){
                    //         $alteSituAnte = $alteracao;
                    //         $alteSituPos = \Zeedhi\Framework\Util\Functions::arrayKeyExists($index+1, $altesitufunc) ? $altesitufunc[$index+1] : null;
                    //     }
                    // }
                    foreach($altesitufunc as $index => $alteracao){
                        $inialtesitu = strtotime($alteracao->getDtinisitufunc()->format('Y-m-d')); 
                        $inialteprox = \Zeedhi\Framework\Util\Functions::arrayKeyExists($index+1, $altesitufunc) ? strtotime($altesitufunc[$index+1]->getDtinisitufunc()->format('Y-m-d')) : 0;
                        
                        
                        if(!empty($dtIniAfast) && $inialtesitu == strtotime($dtIniAfast)){
                            $situRepetida = true;
                        }else if(!empty($dtIniAfast) && $inialtesitu < strtotime($dtIniAfast) && ($inialteprox > strtotime($dtIniAfast) || $inialteprox == 0)){
                            $alteSituAnte = $alteracao;
                            $alteSituPos = \Zeedhi\Framework\Util\Functions::arrayKeyExists($index+1, $altesitufunc) ? $altesitufunc[$index+1] : null;
                        }else if(empty($dtIniAfast) && !empty($dtTermAfast) && ($inialtesitu == strtotime($dtTermAfast) || $inialtesitu < strtotime($dtTermAfast)) && (($inialteprox > strtotime($dtTermAfast)) || $inialteprox == 0)){
                            $alteSituAnte = $alteracao;
                            $alteSituPos = \Zeedhi\Framework\Util\Functions::arrayKeyExists($index+1, $altesitufunc) ? $altesitufunc[$index+1] : null;
                        }
                    }
                    
                    if($situRepetida == true){
                        return array('status' => false,     
                                     'message' => "Foi identificada uma situação com início (".$dtIniAfast."), para o vínculo ".$vinculo[0]->getNrvinculom().", na mesma data da situação que está no XML.");
                    }
                    
                    if(!$alteSituAnte){
                        return array('status' => false,     
                                     'message' => "Não foi encontrado registro de situação funcional para o vínculo ".$vinculo[0]->getNrvinculom()." anterior a ".$this->alterDateFormat($dtAfastamento, 2).".");
                    }
                    
                    if(empty($dtIniAfast) && !empty($dtTermAfast)){
                        
                        if($alteSituAnte && ((!empty($alteSituAnte->getDtfimSituFunc()) && $alteSituAnte->getNrsitufuncm() != 1) || $alteSituAnte->getNrsitufuncm() == 1)){
                            
                            //Procura um gozo sem data fim com início até 30 dias anteriores à data de término do afastamento
                            $dtfimgozoferias = DateUtil::getDataDeString($this->alterDateFormat($dtTermAfast, 2), DateUtil::FORMATO_BRASILEIRO, true);
                            $gozoFerias = current($this->entityManager->getRepository(Repositories::FPA_GOZOFERIAS)->retornaGozosFeriasEntreDatas(
                                $nrorg, $vinculo[0]->getNrvinculom(), DateUtil::subtraiIntervalo($dtfimgozoferias, 30), $dtfimgozoferias
                            ));
                            
                            if($gozoFerias){
                                $gozoFerias->setDtfimgozoferias($dtfimgozoferias);
                                $this->entityManager->persist($gozoFerias);
                                $this->entityManager->flush();
                                
                                array_push($mensagens, "Foi realizada a inclusão da data fim do período de gozo de código ".$gozoFerias->getNrgozoferias()." para o vínculo ".$vinculo[0]->getNrvinculom().".");
                            }else{
                                return array('status' => false,     
                                             'message' => "Não foi encontrada alteração de situação funcional sem data fim, para o vínculo ".$vinculo[0]->getNrvinculom().", para incluir a data ".$this->alterDateFormat($dtTermAfast, 2).".");
                            }
                        } else {
                            $dtinisitunovo = DateUtil::adicionaIntervalo($this->alterDateFormat($dtTermAfast, 2), 1, DateUtil::DIA);
                            $dtfimsitunovo = !empty($alteSituPos) ? DateUtil::subtraiIntervalo($alteSituPos->getDtinisitufunc(), 1, DateUtil::DIA): null;
                            
                            // alteração data fim 
                            $alteSituAnte->setDtfimSituFunc(DateUtil::getDataDeString($this->alterDateFormat($dtTermAfast, 2), DateUtil::FORMATO_BRASILEIRO, true));
                        
                            $this->entityManager->persist($alteSituAnte);
                            $this->entityManager->flush();
                        
                            // nova situação normal
                            $novaAlteSituFunc = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 1, $dtinisitunovo, null, null, null, $dtfimsitunovo);
                            array_push($mensagens, "Foi realizada a inclusão da data fim da alteração de situação funcional para o vínculo ".$vinculo[0]->getNrvinculom()." de código: ".$alteSituAnte->getNraltesitufunc().".");
                        }
                        
                    }else if(!empty($dtIniAfast)){
                        
                        if($alteSituAnte->getNrsitufuncm() != 1 && $alteSituAnte->getDtfimsitufunc() && strtotime($alteSituAnte->getDtfimsitufunc()->format('Y-m-d')) >= strtotime($dtIniAfast)){
                            return array('status' => false,     
                                         'message' => "Vínculo ".$vinculo[0]->getNrvinculom()." já se encontra afastado na data ".$this->alterDateFormat($dtIniAfast, 2).".");
                        }else if(!empty($alteSituPos) && !empty($dtTermAfast) && $alteSituPos->getNrsitufuncm() != 1 && strtotime($alteSituPos->getDtinisitufunc()->format('Y-m-d')) <= strtotime($dtTermAfast)){
                            return array('status' => false,     
                                         'message' => "Vínculo ".$vinculo[0]->getNrvinculom()." já se encontra afastado na data ".$this->alterDateFormat($dtTermAfast, 2).".");
                        }
                        
                        $dtfimsitunormal = DateUtil::subtraiIntervalo($this->alterDateFormat($dtIniAfast, 2), 1, DateUtil::DIA);
                        
                        if(is_array($infoAtestado) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('qtdDiasAfast', $infoAtestado)){
                            $qtDiasAfastamento = $infoAtestado['qtdDiasAfast'];  
                        }else if(!empty($dtTermAfast)){
                            $qtDiasAfastamento = $this->retornaQtDias(DateUtil::getDataDeString($this->alterDateFormat($dtIniAfast, 2), DateUtil::FORMATO_BRASILEIRO, true), DateUtil::getDataDeString($this->alterDateFormat($dtTermAfast, 2), 
                                                                      DateUtil::FORMATO_BRASILEIRO, true));  
                        }else{
                            $qtDiasAfastamento = null;
                        }
                        $codMotAfast = $iniAfastamento && \Zeedhi\Framework\Util\Functions::arrayKeyExists('codMotAfast', $iniAfastamento) ? $iniAfastamento['codMotAfast'] : null; 
                        if($codMotAfast == '01'){
                            $motivoAfastamento = 70;
                            $nrsitufuncm = 16;
                        }else if($codMotAfast == '03'){
                            $motivoAfastamento = 22;
                            $nrsitufuncm = 15;
                        }else{
                            $motivo = $this->entityManager->getRepository(Repositories::GPE_MOTIVOAFASTA)->retornaMotivoAfastPorCdesocial($nrorg, $nrorgpadrao, $codMotAfast);
                            $motivoAfastamento = is_object($motivo) ? $motivo->getNrmotivoafasta() : 70;
                            $nrsitufuncm = 16;
                        }
                        
                        if(!empty($infoAtestado)){
                            $cddiagnost = isset($infoAtestado['codCID']) ? $infoAtestado['codCID'] : null;
                        }else{
                            $cddiagnost = null;
                        }
                        
                        if($cddiagnost){
                            $diagnost = $this->entityManager->getRepository(Repositories::DIAGNOST)->findOneBy(array('cddiagnost' => $cddiagnost));
                            $codigoCDI = $diagnost->getCdtabecdi();
                        }else{
                            $codigoCDI = null;
                        }
                        
                        if($emitente){
                            
                            if($emitente['ideOC'] == '1'){
                                $nrconselhoreg = 3;
                            }else if($emitente['ideOC'] == '2'){
                                $nrconselhoreg = 9;
                            }else{
                                $nrconselhoreg = null;
                            }
                            
                            $pessoaMedico = $this->entityManager->getRepository(Repositories::GPE_PESSOAH)->retornaPessoaConselhoRegional($nrorg, $nrconselhoreg, $emitente['nrOc'], $competencia);
                            $medico = !empty($pessoaMedico) ? $pessoaMedico[0]['nrpessoa'] : null;
                        }else{
                            $medico = null;
                        }
                        
                        $observacao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('observacao', $iniAfastamento) ? $iniAfastamento['observacao'] : null;
                        
                        // alteração do fim da situação funcional anterior
                        $alteSituAnte->setDtfimsitufunc($dtfimsitunormal);
                        
                        $this->entityManager->persist($alteSituAnte);
                        $this->entityManager->flush();
                        
                        // inclusão da situação funcional xml
                        $novaaltesitu = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), $nrsitufuncm, DateUtil::getDataDeString($this->alterDateFormat($dtIniAfast, 2), DateUtil::FORMATO_BRASILEIRO, true), $motivoAfastamento, $cddiagnost, $codigoCDI, 
                                                                DateUtil::getDataDeString($this->alterDateFormat($dtTermAfast, 2), DateUtil::FORMATO_BRASILEIRO, true), null, null, null, 1, $qtDiasAfastamento, $observacao, $medico);
                        
                        array_push($mensagens, "Foi realizada a inclusão da alteração de situação funcional para o vínculo ".$vinculo[0]->getNrvinculom()." de código: ".$novaaltesitu->getNraltesitufunc().".");
                        array_push($mensagens, "Verifique o campo de motivo de afastamento, foi incluído o tipo ".$motivoAfastamento." por padrão de acordo com o 'codMotAfast': ".$codMotAfast.".");
                        array_push($mensagens, "Verifique o campo de situação funcional, foi incluído o tipo ".$nrsitufuncm." por padrão de acordo com o 'codMotAfast': ".$codMotAfast.".");
                        
                        if(!empty($dtTermAfast)){
                            if(!empty($alteSituPos) && $alteSituPos->getNraltesitufunc() == 1){
                                $dtinisitunovo = DateUtil::adicionaIntervalo($this->alterDateFormat($dtTermAfast, 2), 1, DateUtil::DIA);
                                $alteSituPos->setDtinisitufunc($dtinisitunovo);
                                
                                $this->entityManager->persist($alteSituPos);
                                $this->entityManager->flush();
                            }else{
                                $dtinisitunovo = DateUtil::adicionaIntervalo($this->alterDateFormat($dtTermAfast, 2), 1, DateUtil::DIA);
                                $dtfimsitunovo = !empty($alteSituPos) ? DateUtil::subtraiIntervalo($alteSituPos->getDtinisitufunc(), 1, DateUtil::DIA): null;
                                
                                $novaAlteSituFunc = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 1, $dtinisitunovo, null, null, null, $dtfimsitunovo);
                            }
                        
                        }else{
                            array_push($mensagens, "A alteração de situação funcional ".$novaaltesitu->getNraltesitufunc()." foi incluída para o vínculo ".$vinculo[0]->getNrvinculom()." sem uma data fim.");
                        }
                    }
                }
                
                return array('status'   => true,     
                             'messages' => $mensagens);
            }else{
                return array('status' => false,     
                             'message' => "Não foi possível encontrar um vínculo. Verfifique se os dados do XML correspondem aos do vínculo (".$dadosVinculo.").");    
            }
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtAfastTemp' no arquivo).");
        }
    }
    
}
