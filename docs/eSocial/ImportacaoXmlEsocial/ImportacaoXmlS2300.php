<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2300 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2300';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        $nrtipoestrutlegal = $this->nrtipoestrutlegal;
        $nrtipoestrutgeren = $this->nrtipoestrutgeren;
        
        $mensagens = array();
        
        $evtTSVInicio = (array) $this->xml->evtTSVInicio;
        
        if($evtTSVInicio){
            $trabalhador = (array) $evtTSVInicio['trabalhador'];
            $infoTSVInicio = (array) $evtTSVInicio['infoTSVInicio'];
            $dtmescompetenc = DateUtil::getDataDeString($this->alterDateFormat($infoTSVInicio['dtInicio'], 1), DateUtil::FORMATO_BRASILEIRO, true);
            
            $pessoaExistente = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $competencia, $trabalhador['cpfTrab']);
            
            // inserção de Pessoa
            if(empty($pessoaExistente)){
                
                // trabalhador
                $nascimento = (array) $trabalhador['nascimento'];
                $documentos =  \Zeedhi\Framework\Util\Functions::arrayKeyExists('documentos', $trabalhador) ? (array) $trabalhador['documentos'] : null;
                $endereco = isset($trabalhador['endereco']) ? (array) $trabalhador['endereco'] : null;
                $infoDeficiencia = isset($trabalhador['infoDeficiencia']) ? (array) $trabalhador['infoDeficiencia'] : null;
                $contato = \Zeedhi\Framework\Util\Functions::arrayKeyExists('contato', $trabalhador) ? (array) $trabalhador['contato'] : null;
                $trabEstrangeiro = \Zeedhi\Framework\Util\Functions::arrayKeyExists('trabEstrangeiro', $trabalhador) ? (array) $trabalhador['trabEstrangeiro'] : null;
                $estCiv = isset($dadosTrabalhador['estCiv']) ? $dadosTrabalhador['estCiv'] : null;
                $racaCor = isset($dadosTrabalhador['racaCor']) ? $dadosTrabalhador['racaCor'] : null;
                $grauInstr = isset($dadosTrabalhador['grauInstr']) ? $dadosTrabalhador['grauInstr'] : null;
                
                // documentos
                $ctps = !empty($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('CTPS', $documentos) ? (array) $documentos['CTPS'] : null;
                $rg = !empty($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('RG', $documentos) ? (array) $documentos['RG'] : null;
                $rne = !empty($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('RNE', $documentos) ? (array) $documentos['RNE'] : null;
                $cnh = !empty($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('CNH', $documentos) ? (array) $documentos['CNH'] : null;
                
                // nascimento
                $paisNac = isset($nascimento['paisNac']) ? $nascimento['paisNac'] : null;
                $paisNascto = isset($nascimento['paisNascto']) ? $nascimento['paisNascto'] : null;
                $codMunic = isset($nascimento['codMunic']) ? $nascimento['codMunic'] : null;
                $dtNascto = isset($nascimento['dtNascto']) ? $nascimento['dtNascto'] : null;
                $ufNascto = isset($nascimento['uf']) ? $nascimento['uf'] : null;
                
                $estadoCivil = $this->entityManager->getRepository(Repositories::ESTADOCIVIL)->findOneBy(array('cdesocial' => $estCiv));
                $raca = $this->entityManager->getRepository(Repositories::GPE_RACAPESSOA)->findOneBy(array('cdesocial' => $racaCor));
                $grauinstr = $this->entityManager->getRepository(Repositories::GPE_GRAUINSTR)->findOneBy(array('cdesocial' => $grauInstr));
                $paisNac = $this->entityManager->getRepository(Repositories::PAIS)->findOneBy(array('cdesocial' => $paisNac, 'nrorg' => array($nrorg, $nrorgpadrao)));
                $nacionalidade = $this->entityManager->getRepository(Repositories::GPE_NACIONALIDADE)->findOneBy(array('cdpais' => $paisNac->getCdpais())); 
                $paisNascto = $this->entityManager->getRepository(Repositories::PAIS)->findOneBy(array('cdesocial' => $paisNascto, 'nrorg' => array($nrorg, $nrorgpadrao)));
                $codMunic = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('cdmunicibge' => $codMunic, 'nrorg' => array($nrorg, $nrorgpadrao)));
                
                $cdEstacivil = is_object($estadoCivil) ? $estadoCivil->getCdestacivil() : null;
                $nrGrauinstr = is_object($grauinstr) ? $grauinstr->getNrgrauinstr() : null;
                $nrNacionalidade = is_object($nacionalidade) ? $nacionalidade->getNrnacionalidade() : null;
                $municNascto = is_object($codMunic) ? $codMunic->getCdmunicipio() : null;
                
                $dtnascimento = $this->alterDateFormat($dtNascto, 2);
                
                if($infoDeficiencia){
                    $nrCondicaoFisica = $this->retornaCondicaoFisica($infoDeficiencia);
                }else{
                    $nrCondicaoFisica = 1;
                }
                
                if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('nisTrab', $trabalhador)){
                    $validaPis = $this->validaPis($trabalhador['nisTrab']);
                    
                    if($validaPis){
                        $nrPIS = $trabalhador['nisTrab'];
                        $nrnitpessoa = null;
                    }else{
                        $nrPIS = null;
                        $nrnitpessoa = $trabalhador['nisTrab'];
                    }
                    
                }else{
                    $nrPIS = null;
                    $nrnitpessoa = null;
                }
                
                if(empty($ctps)){
                    $ctps['nrCtps'] = null;
                    $ctps['serieCtps'] = null;
                    $ctps['ufCtps'] = null;
                }
                
                if(empty($rg)){
                    $rg['nrRg'] = null;
                    $rg['orgaoEmissor'] = null;
                    $rg['dtExped'] = null;
                }else{
                    if(isset($rg['dtExped'])){
                        $rg['dtExped'] = $this->alterDateFormat($rg['dtExped'], 2);
                    }else{
                        $rg['dtExped'] = null;
                    }
                }
                
                if(empty($rne)){
                    $rne['nrRne'] = null;
                    $rne['orgaoEmissor'] = null;
                    $rne['dtExped'] = null;
                }else{
                    if(isset($rne['dtExped'])){
                        $rne['dtExped'] = $this->alterDateFormat($rne['dtExped'], 2);
                    }else{
                        $rne['dtExped'] = null;
                    }
                }
                
                if(empty($cnh)){
                    $cnh['nrRegCnh'] = null;
                    $cnh['dtExped'] = null;
                    $cnh['ufCnh'] = null;
                    $cnh['dtValid'] = null;
                    $cnh['dtPriHab'] = null;
                    $cnh['categoriaCnh'] = null;
                }else{
                    if(isset($cnh['dtExped'])){
                        $cnh['dtExped'] = $this->alterDateFormat($cnh['dtExped'], 2);
                    }else{
                        $cnh['dtExped'] = null;
                    }
                }
                
                if(empty($trabEstrangeiro)){
                    $trabEstrangeiro['dtChegada'] = null;
                    $trabEstrangeiro['classTrabEstrang'] = null;
                }else{
                    $classTrabEstrang = $this->entityManager->getRepository(Repositories::GPE_CLASSESTRANG)->findOneBy(array('cdesocial' => $trabEstrangeiro['classTrabEstrang']));
                    $trabEstrangeiro['classTrabEstrang'] = $classTrabEstrang->getNrclassestrang();
                }
                    
                // insere parceiro de negocio
                $parceiro = $this->novoParcNegocio($nrorg, $trabalhador['nmTrab'], $trabalhador['nmTrab'], 'PESSOA', 'S', 'N',
                                                    'CPF', $trabalhador['cpfTrab'], DateUtil::getDataDeString($dtnascimento), 'S', 'N');
                
                // insere pessoa 
                $nascimentoUf = isset($nascimento['uf']) ? $nascimento['uf'] : null;
                $pessoa = $this->novaPessoa($nrorg, $parceiro->getNrparcnegocio(), $dtmescompetenc, $trabalhador['nmTrab'], null, null, DateUtil::getDataDeString($dtnascimento), $trabalhador['sexo'], $nrCondicaoFisica, $trabalhador['cpfTrab'], $ctps['nrCtps'], $ctps['serieCtps'], 
                                            $ctps['ufCtps'], null, $nrPIS, null, null, null, $cdEstacivil, null, null, null, null, null, null, $cnh['nrRegCnh'], DateUtil::getDataDeString($cnh['dtExped']), DateUtil::getDataDeString($cnh['dtValid']), $cnh['categoriaCnh'],
                                            $cnh['ufCnh'], null, null, null, null, null, $raca->getNrracapessoa(), null, null, $paisNascto->getCdpais(), $nascimentoUf, $municNascto, $rg['nrRg'], $rg['orgaoEmissor'], null, null, DateUtil::getDataDeString($rg['dtExped']),
                                            $nrNacionalidade, $nrGrauinstr, null, null, $rne['nrRne'], null, null, null, null, null, null, null, null, null, null, null, null, null, $trabEstrangeiro['classTrabEstrang'], $rne['orgaoEmissor'], 
                                            DateUtil::getDataDeString($trabEstrangeiro['dtChegada']), null, $nrnitpessoa);
                
                // insere enderecoparc
                if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('brasil', $endereco)){
                    $enderecoBrasil = (array) $endereco['brasil'];
                    
                    $codMunic = isset($enderecoBrasil['codMunic']) ? $enderecoBrasil['codMunic'] : null;
                    $tpLograd = isset($enderecoBrasil['tpLograd']) ? $enderecoBrasil['tpLograd'] : null;
                    $complemento = isset($enderecoBrasil['complemento']) ? $enderecoBrasil['complemento'] : null;
                    $uf = isset($enderecoBrasil['uf']) ? $enderecoBrasil['uf'] : null;
                    $bairro = isset($enderecoBrasil['bairro']) ? $enderecoBrasil['bairro'] : null;
                    $cep = isset($enderecoBrasil['cep']) ? $enderecoBrasil['cep'] : null;
                    $nrLograd = isset($enderecoBrasil['nrLograd']) ? $enderecoBrasil['nrLograd'] : null;
                    $dscLograd = isset($enderecoBrasil['dscLograd']) ? $enderecoBrasil['dscLograd'] : null;
                    
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('cdmunicibge' => $codMunic, 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $tpLograd = $this->entityManager->getRepository(Repositories::LOGRADOURO)->findOneBy(array('cdesocial' => $tpLograd, 'nrorg' => array($nrorg, $nrorgpadrao)));
                    
                    $cdlogradouro = is_object($tpLograd) ? $tpLograd->getCdlogradouro() : null;
                    $complemento = isset($complemento) ? $complemento : null;
                    $enderecoBrasil = $this->novoEndereco($parceiro->getNrparcnegocio(), '0055', $uf, $cidade->getCdmunicipio(), $cdlogradouro, $bairro, 'PRINCIPAL', $cep, $complemento, 
                                                          $nrLograd, $dscLograd, null);
                    unset($cidade);
                    unset($tpLograd);
                }
                if(\Zeedhi\Framework\Util\Functions::arrayKeyExists('exterior', $endereco)){
                    $enderecoExterior = (array) $endereco['exterior']; 
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('cdmunicibge' => $enderecoExterior['codMunic'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $tpLograd = $this->entityManager->getRepository(Repositories::LOGRADOURO)->findOneBy(array('cdesocial' => $enderecoExterior['tpLograd'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $pais = $this->entityManager->getRepository(Repositories::PAIS)->findOneBy(array('cdesocial' => $enderecoExterior['paisResid'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    
                    $cdlogradouro = is_object($tpLograd) ? $tpLograd->getCdlogradouro() : null;
                    $enderecoExterior = $this->novoEndereco($parceiro->getNrparcnegocio(), $pais->getCdpais(), null, $cidade->getCdmunicipio(), $cdlogradouro, $enderecoExterior['bairro'], 'EXTERIOR', $enderecoExterior['codPostal'], $enderecoExterior['complemento'], 
                                                            $enderecoExterior['nrLograd'], $enderecoExterior['dscLograd'], null);
                    unset($cidade);
                    unset($tpLograd);
                    unset($pais);
                }
                // insere formas de contato
                
                $arrayContato = [];
                if(isset($contato['fonePrinc'])){
                    $fonePrinc['CDFORMACOMU'] = '01';
                    $fonePrinc['NRPARCNEGOCIO'] = $parceiro->getNrparcnegocio();
                    
                    if(strlen($contato['fonePrinc']) > 9){
                        $fonePrinc['CDPREFIXCOMUPARC'] = substr($contato['fonePrinc'], 0, 2);
                        $fonePrinc['CDCOMUNICAPARC'] = substr($contato['fonePrinc'], 2, (strlen($contato['fonePrinc'])-2));
                    }else{
                        $fonePrinc['CDPREFIXCOMUPARC'] = '';
                        $fonePrinc['CDCOMUNICAPARC'] = $contato['fonePrinc'];
                    }
                    
                    array_push($arrayContato, $fonePrinc);
                    unset($fonePrinc);
                }
                if(isset($contato['foneAlternat'])){
                    $foneAlternat['CDFORMACOMU'] = '02';
                    $foneAlternat['NRPARCNEGOCIO'] = $parceiro->getNrparcnegocio();
                    if(strlen($contato['foneAlternat']) > 9){
                        $foneAlternat['CDPREFIXCOMUPARC'] = substr($contato['foneAlternat'], 0, 2);
                        $foneAlternat['CDCOMUNICAPARC'] = substr($contato['foneAlternat'], 2, (strlen($contato['foneAlternat'])-2));
                    }else{
                        $foneAlternat['CDPREFIXCOMUPARC'] = '';
                        $foneAlternat['CDCOMUNICAPARC'] = $contato['foneAlternat'];
                    }
                    
                    array_push($arrayContato, $foneAlternat);
                    unset($foneAlternat);
                }
                if(isset($contato['emailPrinc'])){
                    
                    $emailPrinc['CDFORMACOMU'] = '05';
                    $emailPrinc['NRPARCNEGOCIO'] = $parceiro->getNrparcnegocio();
                    $emailPrinc['CDPREFIXCOMUPARC'] = '';
                    $emailPrinc['CDCOMUNICAPARC'] = $contato['emailPrinc'];
                    
                    array_push($arrayContato, $emailPrinc);
                    unset($emailPrinc);
                }
                
                if(!empty($arrayContato)){
                    $this->novasFormasComunica($arrayContato);
                }
                
                // inserir o pais
                if(isset($nascimento['nmMae'])){
                    $parceiroMae = $this->novoParcNegocio($nrorg, $nascimento['nmMae'], $nascimento['nmMae'], 'PESSOA', 'S', 'N', 'LIVRE', null, null, 'S', 'N'); 
                    $pessoaMae = $this->novaPessoa($nrorg, $parceiroMae->getNrparcnegocio(), $dtmescompetenc, $nascimento['nmMae'], null, null, null, 'F', null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                   null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
                    $relacionaMae = $this->novoRelacionaparc($nrorg, 1, $parceiro->getNrparcnegocio(), null, $parceiroMae->getNrparcnegocio());
                }
                if(isset($nascimento['nmPai'])){
                    $parceiroPai = $this->novoParcNegocio($nrorg, $nascimento['nmPai'], $nascimento['nmPai'], 'PESSOA', 'S', 'N', 'LIVRE', null, null, 'S', 'N'); 
                    $pessoaPai = $this->novaPessoa($nrorg, $parceiroPai->getNrparcnegocio(), $dtmescompetenc, $nascimento['nmPai'], null, null, null, 'M', null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                   null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
                    $relacionaPai = $this->novoRelacionaparc($nrorg, 2, $parceiro->getNrparcnegocio(), null, $parceiroPai->getNrparcnegocio());
                }
                
                $nrPessoa = $pessoa[0]->getNrpessoa();
                $nrParcnegocio = $pessoa[0]->getNrparcnegocio();
                
            }else{
                $nrPessoa = $pessoaExistente[0]['NRPESSOA'];
                $nrParcnegocio = $pessoaExistente[0]['NRPARCNEGOCIO'];
            }
            
            $ideEmpregador = \Zeedhi\Framework\Util\Functions::arrayKeyExists('ideEmpregador', $evtTSVInicio) ? (array) $evtTSVInicio['ideEmpregador'] : null;
            $infoComplementares = (array) $infoTSVInicio['infoComplementares'];
            $cargoFuncao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('cargoFuncao', $infoComplementares) ? (array) $infoComplementares['cargoFuncao'] : null;
            $remuneracao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('remuneracao', $infoComplementares) ? (array) $infoComplementares['remuneracao'] : null;
            $FGTS = \Zeedhi\Framework\Util\Functions::arrayKeyExists('fgts', $infoComplementares) ? (array) $infoComplementares['fgts'] : null;
            $infoDirigenteSindical = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoDirigenteSindical', $infoComplementares) ? (array) $infoComplementares['infoDirigenteSindical'] : null;
            $infoTrabCedido = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoTrabCedido', $infoComplementares) ? (array) $infoComplementares['infoTrabCedido'] : null;
            $infoEstagiario = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoEstagiario', $infoComplementares) ? (array) $infoComplementares['infoEstagiario'] : null;
            $instEnsino = !empty($infoEstagiario) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('instEnsino', $infoEstagiario) ? (array) $infoEstagiario['instEnsino'] : null;
            $ageIntegracao = !empty($infoEstagiario) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('ageIntegracao', $infoEstagiario) ? (array) $infoEstagiario['ageIntegracao'] : null;
            $supervisorEstagio = !empty($infoEstagiario) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('supervisorEstagio', $infoEstagiario) ? (array) $infoEstagiario['supervisorEstagio'] : null;
            $termino = \Zeedhi\Framework\Util\Functions::arrayKeyExists('termino', $infoTSVInicio) ? (array) $infoTSVInicio['termino'] : null;
            
            $nrestrutsind = null;
            $nrEscalaTrab = null;
            
            switch($infoTSVInicio['codCateg']){
                case '901': case '902': case '903': case '904': case '905':
                    $nrtipovinculom = "2";
                    break;
                case '721': case '722': case '723':
                    $nrtipovinculom = "3";
                    break;
                case '701': case '711': case '712': case '712': case '731': case '734': case '738': case '741': case '751': case '761': case '771': case '781': 
                    $nrtipovinculom = "10";
                    break;
                default:
                    $nrtipovinculom = null;
            }
            
            if($nrtipovinculom == "2"){
                $nrvinculoempreg = 20;
                $idTipoSalario = 'MENSAL';
                $idremuneracao = 'ESTAGIO';
            }else if($nrtipovinculom == "3"){
                $nrvinculoempreg = 14;
                $idTipoSalario = 'MENSAL';
                $idremuneracao = 'SOCIO';
            }else{
                $nrtipovinculom = "10";
                $nrvinculoempreg = 21;
                $idTipoSalario = 'MENSAL';
                $idremuneracao = 'AUTONOMO';
            }
            
            $dtAdmissao = $this->alterDateFormat($infoTSVInicio['dtInicio'], 2);
            $nrtpmovtransfm = 1;
            $nrtpregimeprev = $infoTrabCedido && \Zeedhi\Framework\Util\Functions::arrayKeyExists('$infoTrabCedido', $infoTrabCedido) ? $infoTrabCedido['$infoTrabCedido'] : null; 
            
            if(!empty($infoDirigenteSindical)){
                $estrutSind = $this->entityManager->getRepository(Repositories::ESTRUTURAM)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $infoDirigenteSindical['cnpjOrigem'], 10, $dtmescompetenc);
                $nrestrutsind = !empty($estrutSind) ? $estrutSind[0]->getNrestruturam() : null; 
                $validaSindical = true;
            }else{
                $validaSindical = false;
                $nrestrutsind = null;
            }
            
            $dtOpcaoFGTS = $FGTS && \Zeedhi\Framework\Util\Functions::arrayKeyExists('opcFGTS', $FGTS) && $FGTS['opcFGTS'] == 1 ? DateUtil::getDataDeString($this->alterDateFormat($FGTS['dtOpcFGTS'], 2)) : DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true);
            
            if(!empty($cargoFuncao)){
                if(isset($cargoFuncao['codCargo'])){
                    $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($cargoFuncao['codCargo'], $nrorg, $competencia);
                    $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
                } else {
                    $nrcargo = null;
                }
                
                if(isset($cargoFuncao['codFuncao'])){
                    $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($cargoFuncao['codFuncao'], $nrorg, $dtmescompetenc); 
                    $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null; 
                } else {
                    $nrfuncao = null;
                }
            }else{
                $nrcargo = null;
                $nrfuncao = null;
            }
            
            if($infoDirigenteSindical && \Zeedhi\Framework\Util\Functions::arrayKeyExists('matricOrig', $infoDirigenteSindical)){
                $cdmatricula = $infoDirigenteSindical['matricOrig'];
            }else if($infoTrabCedido && \Zeedhi\Framework\Util\Functions::arrayKeyExists('matricCed', $infoTrabCedido)){
                $cdmatricula = $infoDirigenteSindical['matricCed'];
            }else{
                $cdmatricula = null;
            }
            
            $observacaoSalario = !empty($remuneracao) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('dscSalVar', $remuneracao) ? $remuneracao['dscSalVar'] : null;
            if(!empty($remuneracao)){
                $vrSalario = $remuneracao['vrSalFx'];
            }else if($infoEstagiario && \Zeedhi\Framework\Util\Functions::arrayKeyExists('vlrBolsa', $infoEstagiario)){
                $vrSalario = $infoEstagiario['vlrBolsa'];
            }else{
                $vrSalario = null;
            }
            
            $estrutlegal = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->getEstruturaPorNrInsc($nrorg, $competencia, $ideEmpregador['nrInsc'], $ideEmpregador['tpInsc']);
            $nrestrutlegal = !empty($estrutlegal) ? $estrutlegal->getNrestruturam() : null;
            
            if(is_null($nrestrutlegal)){
                return array('status' => false, 
                             'message' => 'Não foi possível encontrar uma estrutura legal com a inscrição '.$ideEmpregador['nrInsc'].' para cadastrar o vínculo.');
            }
            
            $estrutgeren = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $estrutlegal->getCdcnpjestrut(), $nrtipoestrutgeren, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true));
            $nrestrutgeren = !empty($estrutgeren) ? $estrutgeren[0]->getNrestruturam() : null;
            
            //Caso não encontre uma estrutura gerencial com o cnpj da legal cadastra uma nova somente para conseguir inserir o historico do vínculo com estrutura gerencial
            if(is_null($nrestrutgeren)){
                $nrestrutgeren = $this->novaEstruturaGerencial($estrutlegal->getNmestruturah(), $estrutlegal->getCdcnpjestrut(), '01/01/2000');
            }
            
            if($termino){
                $nrsitufuncm = 13;
                $dtRescisao = $termino['dtTerm'];
            }else{
                $nrsitufuncm = 1;
                $dtRescisao = null;
            }
            
            //Verifica se já existe um vínculo para a pessoa com o mesmo tipo de vínculo para mesma estrutura
            $vinculoExistente = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaVinculoPessoaPorTipoVinculo($nrorg, $nrPessoa, $nrtipovinculom, $dtmescompetenc, $nrestrutlegal, $nrvinculoempreg);
            if(is_object($vinculoExistente)){
                return array('status' => false,     
                             'message' => "Esse vínculo já foi inserido. Número:".$vinculoExistente->getNrvinculom()."");
            }
            
            // insere vínculo
            $vinculo = $this->novoVinculo($nrPessoa, DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $cdmatricula, $nrtipovinculom, 1, $nrvinculoempreg, DateUtil::getDataDeString($dtOpcaoFGTS, DateUtil::FORMATO_BRASILEIRO, true), 
                                          DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $trabalhador['nmTrab'],null, null, 
                                          DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $dtmescompetenc, $nrsitufuncm, $nrcargo, $nrEscalaTrab, null, null, null, DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $idremuneracao, 
                                          $idTipoSalario, $nrestrutlegal, $nrestrutgeren, 1, 'UNICO', $nrfuncao, null, $nrtpmovtransfm, null, $nrestrutsind, 'N', $nrorg, DateUtil::getDataDeString($dtRescisao, DateUtil::FORMATO_BRASILEIRO, true), null, 
                                          DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), null, null, null, null);
            if($vinculo[0]->getCdmatricula() == null){
                $vinculo[0]->setCdmatricula($vinculo[0]->getNrvinculom());
            }
            array_push($mensagens, $this->msgSuccess . ' Número do vínculo: '.$vinculo[0]->getNrvinculom().'.');
            //array_push($mensagens, 'Inserir movimentação para uma estrutura gerencial para o vínculo '.$vinculo[0]->getNrvinculom());
            array_push($mensagens, 'Inserir escala de trabalho para o vínculo '.$vinculo[0]->getNrvinculom());
            
            // insere altesalario
            if(!empty($vrSalario)){
                $alteSalario = $this->novaAlteSalario($nrorg, $vinculo[0]->getNrvinculom(), DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), 1, 1, $vrSalario, $idTipoSalario, 1, $observacaoSalario, null, null, null);
            }else{
                array_push($mensagens, $vinculo[0]->getNrvinculom().': Não foi possível cadastrar uma alteração de salário, pois o valor não foi informado.');
            }
            
            //  insere movimentacao legal
            if($nrestrutlegal){
                $movimLegal = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $nrestrutlegal, DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $nrtipoestrutlegal, $nrtpmovtransfm, null, null, 0, null, null);
                $movimgeren = $this->novaMovimentacao($nrorg, 2, $vinculo[0]->getNrvinculom(), $nrestrutgeren, DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), $nrtipoestrutgeren, $nrtpmovtransfm, null, null, 0, null, null);
                array_push($mensagens, 'Foi inserida uma movimentação com a estrutura legal matriz com início de CNPJ '.$ideEmpregador['nrInsc'].'.');
            }else{
                array_push($mensagens, 'Não foi possível cadastrar uma movimentação com a estrutura legal com início de CNPJ '.$ideEmpregador['nrInsc'].' para o vínculo '.$vinculo[0]->getNrvinculom());
            }
            
            // insere movimentacao sindical
            if($validaSindical == true){
                $movimSind = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $nrestrutsind, DateUtil::getDataDeString($dtAdmissao, DateUtil::FORMATO_BRASILEIRO, true), 10, $nrtpmovtransfm, null, null, 0, null, null);
            }else if($validaSindical == false){
                array_push($mensagens, 'Não foi possível cadastrar uma movimentação com a estrutura sindical de CNPJ '.$infoDirigenteSindical['cnpjOrigem'].' para o vínculo '.$vinculo[0]->getNrvinculom());
            }
            
            // insere instituicão de ensino
            if($instEnsino){
                $msg = $this->insereInstituicaoEnsino($nrorg, $instEnsino, $nrParcnegocio, $dtmescompetenc, $vinculo[0]->getNrvinculom());
                array_push($mensagens, $msg);
            }else if (empty($instEnsino) && $nrtipovinculom == "2"){
                array_push($mensagens, $vinculo[0]->getNrvinculom().': Não foi informada a instituição de ensino para o vínculo '.$vinculo[0]->getNrvinculom());
            }
            
            // insere altesitufunc
            $situFuncional = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 1, DateUtil::getDataDeString($dtAdmissao), null, null, null, null, null, null, null, null, null, null);
            
            // if($afastamento){
            //     $iniAfastamento = $this->alterDateFormat($afastamento['dtIniAfast'], 2);
            //     $motivoAfastamento = $this->entityManager->getRepository(Repositories::GPE_MOTIVOAFASTA)->findBy(array('nrorg' => array($nrorg, $nrorgpadrao), 'cdesocial' => $afastamento['codMotAfast']));
            //     if(count($motivoAfastamento) == 1){
            //         $situFuncional->setDtfimsitufunc(DateUtil::subtraiIntervalo($iniAfastamento, 1, DateUtil::DIA));
            //         $alteafastamento = $this->novaAltesitufunc($nrorg, $vinculo->getNrvinculom(), $motivoAfastamento[0]->getNrmotivoafasta(), DateUtil::getDataDeString($iniAfastamento), null, null, null, null, null, null, null, null, null, null);
            //         array_push($mensagens, $vinculo->getNrvinculom().': Complete o cadastro de alteração de situação funcional (número:'.$alteafastamento->getNraltesitufunc().').');
            //     }else if(count($motivoAfastamento) == 0){
            //         array_push($mensagens, $vinculo->getNrvinculom().': Não foi possível cadastrar uma alteração de situação funcional, pois não foi encontrado afastamento de CDESOCIAL '.$afastamento['codMotAfast'].'.');
            //     }else if(count($motivoAfastamento) > 1){
            //         array_push($mensagens, $vinculo->getNrvinculom().': Não foi possível cadastrar uma alteração de situação funcional, pois foram encontrados vários afastamentos de CDESOCIAL '.$afastamento['codMotAfast'].'.');
            //     }
            // }
            
            if($termino){
                $situFuncional->setDtfimsitufunc(DateUtil::subtraiIntervalo($dtRescisao, 1, DateUtil::DIA));
                $situFuncDesligamento = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 13, DateUtil::getDataDeString($dtRescisao), null, null, null, null, null, null, null, null, null, null);
            }
            
            // insere alteocupacao
            if($nrcargo){
                $cargoMestre = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOM)->findOneBy(array('nrorg' => $cargo->getNrorg(), 'nrocupacaom' => $cargo->getNrocupacaom()));
                $alteOcupacao = $this->novaAlteOcupacao($nrorg, $vinculo[0]->getNrvinculom(), $nrcargo, DateUtil::getDataDeString($dtAdmissao), $cargoMestre->getNrtipoocupacao(), 1, null, null, null, null);
            }
            
            return array('status' => true,     
                         'messages' => $mensagens);
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtTSVInicio' no arquivo).");
        }
    }
    
}
