<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS1030 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-1030';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $dtcompetencia = $this->dtcompetencia;
        $evtTabCargo  = (array) $this->xml->evtTabCargo;
        
        if($evtTabCargo){
            $infoCargo = (array) $evtTabCargo['infoCargo'];
            
            $operacao = $this->getOperacaoEventoCadastro($evtTabCargo['infoCargo']);
            
            $ideCargo = (array) $evtTabCargo['infoCargo']->$operacao->ideCargo; 
            $dadosCargo = (array) $evtTabCargo['infoCargo']->$operacao->dadosCargo;
            
            if(strlen($ideCargo['codCargo']) > 30){
                return array('status' => false, 
                             'message' => 'Código de integração '.$ideCargo['codCargo'].' com tamanho maior que o permitido. Tamanho máximo 30 caracteres.');   
            }
            
            $ocupacao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($ideCargo['codCargo'], $nrorg, $dtcompetencia);
            if(!empty($ocupacao)){
                return array('status' => false, 
                             'message' => 'Já existe uma ocupação cadastrada com esse código de integração '.$ideCargo['codCargo'].'.');   
            }
            
            $dtinivigencia = $this->alterDateFormat($ideCargo['iniValid']);
            
            if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('fimValid', $ideCargo) && !empty($ideCargo['fimValid'])){
                $dtfimvigencia = strlen($ideCargo['fimValid']) < 10 ? $this->alterDateFormat($ideCargo['fimValid']) : $ideCargo['fimValid'];
            }else{
                $dtfimvigencia = null;
            }
            
            $dtmescompetenc = DateUtil::truncateData(DateUtil::getPrimeiroDiaDoMes(DateUtil::getDataDeString($dtinivigencia,DateUtil::FORMATO_BRASILEIRO,true)));
            
            // Salva Ocupação
            $ocupacao = $this->novaOcupacao(1, $dtinivigencia, $dtmescompetenc, $dadosCargo['nmCargo'], $dtfimvigencia, null, null, $ideCargo['codCargo'], 
                                               $dadosCargo['codCBO'], null, null, null, null , null);
            
            return array('status' => true,     
                         'messages' => [$this->msgSuccess . ' Número da ocupação criada: '.$ocupacao[0]->getNrocupacaom()]);
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTabCargo' no arquivo).");
        }
    }
    
}
