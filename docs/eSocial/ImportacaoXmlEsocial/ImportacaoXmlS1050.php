<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1050 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1050';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $dtcompetencia = $this->dtcompetencia;
        $evtTabHorTur  = (array) $this->xml->evtTabHorTur;
        
        if($evtTabHorTur){
            $infoHorContratual = $evtTabHorTur['infoHorContratual'];
            
            $operacao = $this->getOperacaoEventoCadastro($infoHorContratual);
            
            $ideHorContratual = (array) $infoHorContratual->$operacao->ideHorContratual;
            $dadosHorContratual = (array) $infoHorContratual->$operacao->dadosHorContratual;
            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('horarioIntervalo', $dadosHorContratual)){
                $horarioIntervalo = is_array($dadosHorContratual['horarioIntervalo']) ? $dadosHorContratual['horarioIntervalo'] :  [$dadosHorContratual['horarioIntervalo']];
                if(count($horarioIntervalo) > 1){
                    $horarioIntervalo = $this->ordenaDados($horarioIntervalo);
                }
            }else{
                $horarioIntervalo = [];
            }
            
            $cdintegracao = substr($ideHorContratual['codHorContrat'],0,20);
            
            $horario = $this->entityManager->getRepository(Repositories::GPE_HORDIAM)->findOneBy(array('nrorg' => $nrorg, 'cdintegracao' => $cdintegracao));
            
            if(empty($horario)){
                $dtinivigencia = DateUtil::getDataDeString($this->alterDateFormat($ideHorContratual['iniValid'], 1), DateUtil::FORMATO_BRASILEIRO, true);
                
                if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $ideHorContratual)){
                    $dtfimvigencia = DateUtil::getDataDeString($this->alterDateFormat($ideHorContratual['fimValid'], 1), DateUtil::FORMATO_BRASILEIRO, true);
                }else{
                    $dtfimvigencia = null;
                }
                
                $nmhordiah = $dadosHorContratual['hrEntr'].' - '.$dadosHorContratual['hrSaida'];
        
                // Salva Horário
                $horario = $this->novoHorario($nrorg, $dtinivigencia, $dtinivigencia, $nmhordiah, 'N', $dtfimvigencia, $cdintegracao, '0600');
                
                $entrada = $dadosHorContratual['hrEntr'];
                $saida = $dadosHorContratual['hrSaida'];
                $hrintervalo = null;
                $dsintervalo = null;
                $nrtpintervalo = (intval($dadosHorContratual['hrSaida']) - intval($dadosHorContratual['hrEntr'])) < 400 ? 1 : 3;
                $intervalosHorario = [];
                
                // 1	Sem intervalo
                // 2	Intervalo em horário fixo
                // 3	Intervalo em horário variável
                
                for($i = 0; $i< count($horarioIntervalo)+1; $i++){
                    $dados =  \Zeedhi\Framework\Util\Functions::arrayKeyExists($i, $horarioIntervalo) ? (array) $horarioIntervalo[$i] : null;
                    
                    if(!is_null($dados) && !isset($dados['iniInterv'])){
                        continue;
                    }
                    
                    if(count($horarioIntervalo) == $i && count($horarioIntervalo) > 0){
                        $saida = $dadosHorContratual['hrSaida'];
                        $hrintervalo = null;
                        $dsintervalo = null;
                        $nrtpintervalo = null;
                    }else if(count($horarioIntervalo) >= $i && !empty($dados)){
                        $saida = $dados['iniInterv'];
                        $hrintervalo = $this->getHoraDeMinuto($dados['durInterv']);
                        $dsintervalo = $dados['durInterv'] >= '60' ? 'Almoço/Descanso' : 'Lanche';
                        $nrtpintervalo = 2;
                    }
                    
                    $intervalosHorario[] = $this->novoIntervaloHorario($nrorg, $horario[0]->getNrhordiam(), ($i+1), $entrada, $entrada, $entrada, $saida, $saida, $saida, $entrada, $saida, 'DC', 'DC', 'N', 'N', 'N', 'N', $hrintervalo, 'S', $dsintervalo, $nrtpintervalo);
                                                                    
                    if(isset($dados['termInterv'])){
                        $entrada = !empty($dados) ? $dados['termInterv'] : null;
                    }else{
                        $entrada = null;
                    }
                }
                
                return array('status' => true,     
                             'messages' => [$this->msgSuccess . ' Número do horário criado: '.$horario[0]->getNrhordiam()]);
            }else{
                return array('status' => false, 
                             'message' => 'Já existe um horário cadastrado com esse código de integração '.$cdintegracao.'.');   
            }
            
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTabFuncao' no arquivo).");
        }
    }
    
}
