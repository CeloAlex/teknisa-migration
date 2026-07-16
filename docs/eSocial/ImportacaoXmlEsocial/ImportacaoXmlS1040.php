<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1040 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1040';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $dtcompetencia = $this->dtcompetencia;
        $evtTabFuncao  = (array) $this->xml->evtTabFuncao;
        
        if($evtTabFuncao){
            $infoFuncao = (array) $evtTabFuncao['infoFuncao'];
            
            $operacao = $this->getOperacaoEventoCadastro($evtTabFuncao['infoFuncao']);
            
            $ideFuncao = (array) $evtTabFuncao['infoFuncao']->$operacao->ideFuncao; 
            $dadosFuncao = (array) $evtTabFuncao['infoFuncao']->$operacao->dadosFuncao;
            
            if(strlen($ideFuncao['codFuncao']) > 30){
                return array('status' => false, 
                             'message' => 'Código de integração '.$ideFuncao['codFuncao'].' com tamanho maior que o permitido. Tamanho máximo 30 caracteres.');   
            }
            
            $ocupacao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($ideFuncao['codFuncao'], $nrorg, $dtcompetencia);
            if(!empty($ocupacao)){
                return array('status' => false, 
                             'message' => 'Já existe uma ocupação cadastrada com esse código de integração '.$ideFuncao['codFuncao'].'.');   
            }
            
            $dtinivigencia = $this->alterDateFormat($ideFuncao['iniValid']);
            
            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $ideFuncao) && !empty($ideFuncao['fimValid'])){
                $dtfimvigencia = strlen($ideFuncao['fimValid']) < 10 ? $this->alterDateFormat($ideFuncao['fimValid']) : $ideFuncao['fimValid'];
            }else{
                $dtfimvigencia = null;
            }
            
            $dtmescompetenc = DateUtil::truncateData(DateUtil::getPrimeiroDiaDoMes(DateUtil::getDataDeString($dtinivigencia,DateUtil::FORMATO_BRASILEIRO,true)));
            
            // Salva Ocupação
            $ocupacao = $this->novaOcupacao(2, $dtinivigencia, $dtmescompetenc, $dadosFuncao['dscFuncao'], $dtfimvigencia, null, null, $ideFuncao['codFuncao'], 
                                               $dadosFuncao['codCBO'], null, null, null, null , null);
            return array('status' => true,     
                         'messages' => [$this->msgSuccess . ' Número da ocupação criada: '.$ocupacao[0]->getNrocupacaom()]);
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTabFuncao' no arquivo).");
        }
    }
    
}
