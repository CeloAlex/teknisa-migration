<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2200 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2200';
    
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
        
        $evtAdmissao  = (array) $this->xml->evtAdmissao;
        
        if($evtAdmissao){
            $trabalhador = (array) $evtAdmissao['trabalhador'];
            $vinculo = (array) $evtAdmissao['vinculo'];
            $admissao = (array) $vinculo['infoRegimeTrab']->infoCeletista->dtAdm;
            $dtmescompetenc = DateUtil::getDataDeString($this->alterDateFormat($admissao[0], 1),DateUtil::FORMATO_BRASILEIRO,true);
            
            $pessoaExistente = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $dtmescompetenc->format('d/m/Y'), $trabalhador['cpfTrab']);
            $vinculoExistente = $this->entityManager->getRepository(Repositories::GPE_VINCULOH)->retornaVinculoPorMatriculaESocial($nrorg, null, $vinculo['matricula'], $dtmescompetenc, null);
            
            if(!empty($vinculoExistente)){
                return array('status' => false,     
                             'message' => "Vínculo com matrícula esocial ".$vinculo['matricula']." já existente. Número:".$vinculoExistente->getNrvinculom()."");
            }
            
            // inserção de Pessoa
            if(empty($pessoaExistente)){
                
                // dados pessoa
                $nascimento = \Zeedhi\Framework\Util\Functions::arrayKeyExists('nascimento', $trabalhador) ? (array) $trabalhador['nascimento'] : null;
                $documentos = \Zeedhi\Framework\Util\Functions::arrayKeyExists('documentos', $trabalhador) ? (array) $trabalhador['documentos'] : null;
                $nisTrab = isset($trabalhador['nisTrab']) ? $trabalhador['nisTrab'] : null;
                $endereco = \Zeedhi\Framework\Util\Functions::arrayKeyExists('endereco', $trabalhador) ? (array) $trabalhador['endereco'] : null;
                $infoDeficiencia = \Zeedhi\Framework\Util\Functions::arrayKeyExists('infoDeficiencia', $trabalhador) ? (array) $trabalhador['infoDeficiencia'] : null;
                $contato = \Zeedhi\Framework\Util\Functions::arrayKeyExists('contato', $trabalhador) ? (array) $trabalhador['contato'] : null;
                $trabEstrangeiro = \Zeedhi\Framework\Util\Functions::arrayKeyExists('trabEstrangeiro', $trabalhador) ? (array) $trabalhador['trabEstrangeiro'] : null;
                $estCiv = isset($trabalhador['estCiv']) ? $trabalhador['estCiv'] : null;
                $racaCor = isset($trabalhador['racaCor']) ? $trabalhador['racaCor'] : null;
                $grauInstr = isset($trabalhador['grauInstr']) ? $trabalhador['grauInstr'] : null;;
                
                // documentos
                $ctps = !is_null($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('CTPS', $documentos) ? (array) $documentos['CTPS'] : null;
                $rg = !is_null($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('RG', $documentos) ? (array) $documentos['RG'] : null;
                $rne = !is_null($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('RNE', $documentos) ? (array) $documentos['RNE'] : null;
                $cnh = !is_null($documentos) && \Zeedhi\Framework\Util\Functions::arrayKeyExists('CNH', $documentos) ? (array) $documentos['CNH'] : null;
                
                
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
                
                $cdestacivil = is_object($estadoCivil) ? $estadoCivil->getCdestacivil() : null;
                $nrgrauinstr = is_object($grauinstr) ? $grauinstr->getNrgrauinstr() : null;
                $nrnacionalidade = is_object($nacionalidade) ? $nacionalidade->getNrnacionalidade() : null;
                $municNascto = is_object($codMunic) ? $codMunic->getCdmunicipio() : null;
                
                $dtnascimento = $this->alterDateFormat($dtNascto, 2);
                $nrCondicaoFisica = $this->retornaCondicaoFisica($infoDeficiencia);
                $infoCota = isset($infoDeficiencia['infoCota']) ? $infoDeficiencia['infoCota'] : null;
                
                $validaPis = $this->validaPis($nisTrab);
                if($validaPis){
                    $nrPIS = $nisTrab;
                    $nrnitpessoa = null;
                }else{
                    $nrPIS = null;
                    $nrnitpessoa = $nisTrab;
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
                    } else {
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
                    } else {
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
                    } else {
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
                $parceiro = $this->novoParcNegocio($nrorg, $trabalhador['nmTrab'], $trabalhador['nmTrab'], 'PESSOA', 'S', 'N', 'CPF', $trabalhador['cpfTrab'], DateUtil::getDataDeString($dtnascimento)->setTime(0,0), 'S', 'N');
                
                // insere pessoa 
                $nascimentoUf = isset($nascimento['uf']) ? $nascimento['uf'] : null;
                $pessoa = $this->novaPessoa($nrorg, $parceiro->getNrparcnegocio(), $dtmescompetenc, $trabalhador['nmTrab'], null, null, DateUtil::getDataDeString($dtnascimento)->setTime(0,0), $trabalhador['sexo'], $nrCondicaoFisica, $trabalhador['cpfTrab'], $ctps['nrCtps'], $ctps['serieCtps'], 
                                            $ctps['ufCtps'], null, $nrPIS, null, null, null, $cdestacivil, null, null, null, null, null, null, $cnh['nrRegCnh'], DateUtil::getDataDeString($cnh['dtExped']), DateUtil::getDataDeString($cnh['dtValid']), $cnh['categoriaCnh'],
                                            $cnh['ufCnh'], null, null, null, null, null, $raca->getNrracapessoa(), null, null, $paisNascto->getCdpais(), $nascimentoUf, $municNascto, $rg['nrRg'], $rg['orgaoEmissor'], null, null, DateUtil::getDataDeString($rg['dtExped']),
                                            $nrnacionalidade, $nrgrauinstr, null, null, $rne['nrRne'], null, null, null, null, null, null, null, null, null, null, null, null, null, $trabEstrangeiro['classTrabEstrang'], $rne['orgaoEmissor'], 
                                            DateUtil::getDataDeString(isset($trabEstrangeiro['dtChegada']) ? $trabEstrangeiro['dtChegada'] : null), $infoCota, $nrnitpessoa);
                
                // insere enderecoparc
                if($endereco && \Zeedhi\Framework\Util\Functions::arrayKeyExists('brasil', $endereco)){
                    $enderecoBrasil = (array) $endereco['brasil'];
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('cdmunicibge' => $enderecoBrasil['codMunic'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    if(isset($enderecoBrasil['tpLograd'])){
                        $tpLograd = $this->entityManager->getRepository(Repositories::LOGRADOURO)->findOneBy(array('cdesocial' => $enderecoBrasil['tpLograd'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    }else{
                        $tpLograd = null;
                    }
                    
                    $cdMunicipio = is_object($cidade) ? $cidade->getCdmunicipio() : null;
                    $cdLogradouro = is_object($tpLograd) ? $tpLograd->getCdlogradouro() : null;
                    
                    $enderecoBrasil = $this->novoEndereco(
                        $parceiro->getNrparcnegocio(), '0055', (isset($enderecoBrasil['uf']) ? $enderecoBrasil['uf'] : null), $cdMunicipio, $cdLogradouro, isset($enderecoBrasil['bairro']) ? $enderecoBrasil['bairro'] : null, 'PRINCIPAL', $enderecoBrasil['cep'], 
                        isset($enderecoBrasil['complemento']) ? $enderecoBrasil['complemento'] : null, $enderecoBrasil['nrLograd'], $enderecoBrasil['dscLograd'], null
                    );
                    unset($cidade);
                    unset($tpLograd);
                }
                if($endereco && \Zeedhi\Framework\Util\Functions::arrayKeyExists('exterior', $endereco)){
                    $enderecoExterior = (array) $endereco['exterior']; 
                    $pais = $this->entityManager->getRepository(Repositories::PAIS)->findOneBy(array('cdesocial' => $enderecoExterior['paisResid'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('nmmunicipio' => $enderecoExterior['nmCid'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    
                    $cdPais = is_object($pais) ? $pais->getCdpais() : null;
                    $cdMunicipio = is_object($cidade) ? $cidade->getCdmunicipio() : null;
                    
                    $enderecoExterior = $this->novoEndereco(
                        $parceiro->getNrparcnegocio(), $cdPais, null, $cdMunicipio, null, isset($enderecoBrasil['bairro']) ? $enderecoExterior['bairro'] : null, 'EXTERIOR', $enderecoExterior['codPostal'],
                        isset($enderecoExterior['complemento']) ? $enderecoExterior['complemento'] : null, $enderecoExterior['nrLograd'], $enderecoExterior['dscLograd'], null
                    );
                    unset($cidade);
                    unset($pais);
                }
                
                // insere formas de contato
                $arrayContato = [];
                if($contato && \Zeedhi\Framework\Util\Functions::arrayKeyExists('fonePrinc', $contato)){
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
                if($contato && \Zeedhi\Framework\Util\Functions::arrayKeyExists('foneAlternat', $contato)){
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
                if($contato && \Zeedhi\Framework\Util\Functions::arrayKeyExists('emailPrinc', $contato)){
                    
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
                
                // inserir os pais
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
                $nrParcnegocio = $parceiro->getNrparcnegocio();
            }else{
                $nrPessoa = $pessoaExistente[0]['NRPESSOA'];
                $nrParcnegocio = $pessoaExistente[0]['NRPARCNEGOCIO'];
            }
            
            $infoCeletista = (array) $vinculo['infoRegimeTrab']->infoCeletista;
            $infoContrato = isset($vinculo['infoContrato']) ? (array) $vinculo['infoContrato'] : null;
            $horContratual = isset($infoContrato['horContratual']) ? (array) $infoContrato['horContratual'] : null;
            $remuneracao = isset($infoContrato['remuneracao']) ? (array) $infoContrato['remuneracao'] : null;
            $FGTS = isset($infoCeletista['FGTS']) ?(array) $infoCeletista['FGTS'] : null;
            $duracao = \Zeedhi\Framework\Util\Functions::arrayKeyExists('duracao', $infoContrato) ? (array) $infoContrato['duracao'] : null;
            $desligamento = \Zeedhi\Framework\Util\Functions::arrayKeyExists('desligamento', $vinculo) ? (array) $vinculo['desligamento'] : null;
            $dependentes = \Zeedhi\Framework\Util\Functions::arrayKeyExists('dependente', $trabalhador) ? $trabalhador['dependente'] : null;
            $afastamento = \Zeedhi\Framework\Util\Functions::arrayKeyExists('afastamento', $vinculo) ? (array) $vinculo['afastamento'] : null;
            $sucessaoVinc = \Zeedhi\Framework\Util\Functions::arrayKeyExists('sucessaoVinc', $vinculo) ? (array) $vinculo['sucessaoVinc'] : null;
            // $transfDom = (array) $vinculo['transfDom'];
            // $mudancaCPF = (array) $vinculo['mudancaCPF'];
            
            $dtAdmissao = $this->alterDateFormat($infoCeletista['dtAdm'], 2);
            $nrtpmovtransfm = (isset($trabalhador['indPriEmpr']) && $trabalhador['indPriEmpr'] == 'S') ? 1 : 2;
            $nrvinculoempreg = $infoCeletista['natAtividade'] == 1 ? 1 : 4;
            
            $estrutSind = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $infoCeletista['cnpjSindCategProf'], 10, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true));
            if(!$estrutSind && $infoCeletista['cnpjSindCategProf']){
                //Cadastra o sindicato
                $retorno = array();
                $retorno = $this->consultaDadoRF($infoCeletista['cnpjSindCategProf']);
                if($retorno['Status'] == true){
                    $nmestrutura = null;
                    $nmfantasia = null;
                    $iniValid = null;
                    $cdnatujuri = null;
                    $cdcnae = null;
                    if(isset($retorno['RazaoSocial']) && $retorno['RazaoSocial'] != ""){
                        $nmestrutura = $retorno['RazaoSocial'];
                    }
                    if(isset($retorno['NomeFantasia']) && $retorno['NomeFantasia'] != ""){
                        $nmfantasia = $retorno['NomeFantasia'];
                    }
                    if(isset($retorno['DataFundacao']) && $retorno['DataFundacao'] != ""){
                        $iniValid = $retorno['DataFundacao'];
                    }
                    if(isset($retorno['CodigoNaturezaJuridica']) && $retorno['CodigoNaturezaJuridica'] != ""){
                        $cdnatujuri = $retorno['CodigoNaturezaJuridica'];
                    }
                    if(isset($retorno['CodigoAtividadeEconomica']) && $retorno['CodigoAtividadeEconomica'] != ""){
                        $cdcnae = str_replace(array("-","/"), "", $retorno['CodigoAtividadeEconomica']);
                    }
                }else{
                    $nmestrutura = 'Sindicato ' . $infoCeletista['cnpjSindCategProf'];
                    $nmfantasia = 'Sindicato ' . $infoCeletista['cnpjSindCategProf'];
                    $iniValid = '01/01/2000';
                    $cdnatujuri = null;
                    $cdcnae = null;
                }
                
                // Salva Parceiro de Negócio
                $parcnegocio = $this->novoParcNegocio($nrorg, $nmestrutura, $nmestrutura, 'ESTRUTURA', 'N', 'N',
                                                      'CNPJ', $infoCeletista['cnpjSindCategProf'], DateUtil::getDataDeString($iniValid,DateUtil::FORMATO_BRASILEIRO,true), 'S');
                                                
                // Salva Estrutura
                $estrutSind = $this->novaEstrutura(10, $iniValid, 'S', 'N', $parcnegocio->getNrparcnegocio(), $nmestrutura, $infoCeletista['cnpjSindCategProf'], null, null, null, null, null,
                                                  null, null, null, null, null, null, null, null, null, null, $nmestrutura, $cdnatujuri, $cdcnae, null, null, null, null, null, null, null, null, null, $nmfantasia, $nmestrutura,
                                                  null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
                                                  
                array_push($mensagens, 'Criação da estrutura sindical '.$estrutSind[1]->getNmestruturah().' de CNPJ '.$estrutSind[1]->getCdcnpjestrut());
            }
            $nrestrutsind = !empty($estrutSind) ? $estrutSind[0]->getNrestruturam() : null; 
            
            if($FGTS){
                $dtOpcaoFGTS = $FGTS['opcFGTS'] == 1 ? DateUtil::getDataDeString($this->alterDateFormat($FGTS['dtOpcFGTS'], 2)) : null;
            } else {
                $dtOpcaoFGTS = DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true);
            }
            
            if(isset($infoContrato['codCargo'])){
                $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($infoContrato['codCargo'], $nrorg, $dtmescompetenc);
                $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
            } else if(isset($infoContrato['CBOCargo'])){
                $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['CBOCargo'], $nrorg, $dtmescompetenc);
                $nrcargo = !empty($cargo) ? $cargo->getNrocupacaom() : null;
                if(is_null($nrcargo) && isset($infoContrato['nmCargo'])){
                    $cargo = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoNmocupacao($infoContrato['nmCargo'], $nrorg, $dtmescompetenc);
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
                $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCdintegracao($infoContrato['codFuncao'], $nrorg, $dtmescompetenc); 
                $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
            } else if(isset($infoContrato['CBOFuncao'])){
                $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['CBOFuncao'], $nrorg, $dtmescompetenc);
                $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
                if(is_null($nrfuncao) && isset($infoContrato['nmFuncao'])){
                    $funcao = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOH)->retornaUltimoHistoricoCbo($infoContrato['nmFuncao'], $nrorg, $dtmescompetenc);
                    $nrfuncao = !empty($funcao) ? $funcao->getNrocupacaom() : null;
                }
            } else {
                $nrfuncao = null;
            }
            
            if(is_null($nrfuncao) && !is_null($nrcargo)){
                $nrfuncao = $nrcargo;
            }
            
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
                    $idTipoSalario = 'TAREFA';
                    $idremuneracao = 'SAL1';
                    $idTpPagamento = 'TAREFA';
                    break;
            }
            
            $observacaoSalario = (array) $infoContrato['remuneracao'];
            $observacaoSalario = \Zeedhi\Framework\Util\Functions::arrayKeyExists('dscSalVar', $observacaoSalario) ? $observacaoSalario['dscSalVar'] : null;
            
            if($duracao){
                if(isset($duracao['dtTerm'])){
                    $dtfimcontrdetermin = $this->alterDateFormat($duracao['dtTerm'], 2);
                    $dtfimcontrdetermin = DateUtil::getDataDeString($dtfimcontrdetermin)->setTime(0,0);
                }else{
                    $dtfimcontrdetermin = null;
                }
            }else{
                $dtfimcontrdetermin = null;
            }
            
            $nrinsc = (array) $infoContrato['localTrabalho']->localTrabGeral->nrInsc;
            $estrutlegal = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $nrinsc[0], $nrtipoestrutlegal, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true));
            $nrestrutlegal = !empty($estrutlegal) ? $estrutlegal[0]->getNrestruturam() : null;
            $estrutgeren = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $nrinsc[0], $nrtipoestrutgeren, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true));
            $nrestrutgeren = !empty($estrutgeren) ? $estrutgeren[0]->getNrestruturam() : null;
            
            if(is_null($nrestrutlegal)){
                return array('status' => false, 
                             'message' => 'Não foi possível encontrar uma estrutura legal com a inscrição '.$nrinsc[0].' para cadastrar o vínculo.');
            }
            
            //Caso não encontre uma estrutura gerencial com o cnpj da legal cadastra uma nova somente para conseguir inserir o historico do vínculo com estrutura gerencial
            if(is_null($nrestrutgeren)){
                $nrestrutgeren = $this->novaEstruturaGerencial($estrutlegal[1]->getNmestruturah(), $nrinsc[0], '01/01/2000');
            }
            
            $escalaTrab = null;
            if($horContratual){
                $hora = !empty($horContratual['horario']) ? (array) $horContratual['horario'][0] : null;
                if($hora){
                    $escalaTrab = $this->entityManager->getRepository(Repositories::GPE_ESCALATRABM)->retornaEscalaTrabalhoPorHorario($hora['dia'], $hora['codHorContrat'], $horContratual['qtdHrsSem'], $horContratual['tpJornada'], $nrorg, $competencia);
                } else {
                    $escalaTrab = $this->entityManager->getRepository(Repositories::GPE_ESCALATRABM)->retornaEscalaTrabalhoPorQtdHrsSem($horContratual['qtdHrsSem'], $horContratual['tpJornada'], $nrorg, $competencia);
                }
                if(!$escalaTrab){
                    
                    //Nome padrão de escala criada na migração
                    $nmescalatrabh = isset($horContratual['dscTpJorn']) ? $horContratual['dscTpJorn'] : 'Escala da migração '.$horContratual['qtdHrsSem'];
                    
                    //Se não encontrou uma escala com o horário verifica se já existe uma escala criada pela migração com a mesma quantidade de hrs e tipo de jornada para só incluir um novo turno
                    $escala = $this->entityManager->getRepository(Repositories::GPE_ESCALATRABM)->retornaEscalaTrabalhoPorNome($nrorg, $competencia, $nmescalatrabh, $horContratual['qtdHrsSem'], $horContratual['tpJornada']);
                    
                    if(!$escala){
                        //Cadastra nova escala
                        $qthrsemesctrabh = isset($horContratual['qtdHrsSem']) ? $horContratual['qtdHrsSem'] : null;
                        $qthrescalatrabh = null;
                        $descansosemanal = 'ESCALA';
                        
                        $tipojornada = $this->entityManager->getRepository(Repositories::PTO_TIPOJORNADA)->findOneBy(array('cdesocial' => $horContratual['tpJornada']));
                        
                        $escala = $this->novaEscalaTrabalho(
                            $nrorg, null, DateUtil::getDataDeString('01/01/2000',DateUtil::FORMATO_BRASILEIRO,true), 'S', null, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true), 
                            $nmescalatrabh, $descansosemanal, 'N', '0200', 'N', 'S', 'N', 'S', '0100', 'S', 'S', 'S', 'N', 'S', '2200', '0600', 'N', 'N', 'S', 'N', 'N', 'N', 'N', $qthrescalatrabh, $qthrsemesctrabh, null, 
                            null, null, null, null, is_object($tipojornada) ? $tipojornada->getNrtpjornada(): null
                       );
                       
                       array_push($mensagens, 'Criação da escala de trabalho '.$escala[0]->getNrescalatrabm().' - '.$nmescalatrabh);
                    }
                   
                    $turno = $this->novoTurno($nrorg, $escala[0]->getNrescalatrabm(), DateUtil::getDataDeString('01/01/2000',DateUtil::FORMATO_BRASILEIRO,true), 'S', 'Turno');
                   
                    array_push($mensagens, 'Criação do turno '.$turno->getNrturno().' na escala de trabalho '.$escala[0]->getNrescalatrabm().' - '.$nmescalatrabh);
                    
                    $nrhordiam = null;
                    $turnohorario = null;
                    if(isset($horContratual['horario'])){
                        $nrseqhorario = null;
                        $iddiavariavel = 'N';
                        $horarios = is_array($horContratual['horario']) ? $horContratual['horario'] : [$horContratual['horario']];
                        
                        foreach($horarios as $horario){
                            $dia = (string)$horario->dia;
                            $codHorContrat = substr((string)$horario->codHorContrat,0,20);
                            
                            switch($dia){
                                case "1":
                                    $nrseqhorario = 3;
                                    break;
                                case "2":
                                    $nrseqhorario = 4;
                                    break;
                                case "3":
                                    $nrseqhorario = 5;
                                    break;
                                case "4":
                                    $nrseqhorario = 6;
                                    break;
                                case "5":
                                    $nrseqhorario = 7;
                                    break;
                                case "6":
                                    $nrseqhorario = 1;
                                    break;
                                case "7":
                                    $nrseqhorario = 2;
                                    break;
                                case "8":
                                    $nrseqhorario = 1;
                                    $iddiavariavel = 'S';
                                    break;
                                default:
                                    $nrseqhorario = 1;
                                    $iddiavariavel = 'N';
                                    break;
                            }
                            
                            $horariodia = $this->entityManager->getRepository(Repositories::GPE_HORDIAM)->findOneBy(array('nrorg' => $nrorg, 'cdintegracao' => $codHorContrat));
                            if($horariodia){
                                $nrhordiam = $horariodia->getNrhordiam();
                            }else{
                                $nmhordiah = 'Horário da Migração '.$codHorContrat;
                                $horariodia = $this->novoHorarioDia(
                                    $nrorg, DateUtil::getDataDeString('01/01/2000',DateUtil::FORMATO_BRASILEIRO,true), null, DateUtil::getDataDeString($competencia,DateUtil::FORMATO_BRASILEIRO,true),
                                    $nmhordiah, 'N', null, $codHorContrat
                                );
                                
                                array_push($mensagens, 'Criação do horário '.$horariodia[0]->getNrhordiam().'. Favor completar o cadastro na tela Horário.');
                                
                                $nrhordiam = $horariodia[0]->getNrhordiam();
                            }
                            
                            $turnohorario = $this->novoTurnoHorario($nrorg, $turno->getNrturno(), $nrhordiam, $nrseqhorario, 'S', $iddiavariavel);
                        }
                    }
                    
                    $escalaTrab = array(
                        'nrescalatrabm' => $escala[0]->getNrescalatrabm(),
                        'nrturno' => $turno->getNrturno(),
                        'nrhordiam' => $nrhordiam,
                        'nrhorarioturno' => is_object($turnohorario) ? $turnohorario->getNrhorarioturno() : null,
                    );
                }
            }
            
            $nrEscalaTrab = isset($escalaTrab['nrescalatrabm']) ? $escalaTrab['nrescalatrabm'] : null;
            
            if($desligamento){
                $nrsitufuncm = 13;
                $dtRescisao = $desligamento['dtDeslig'];
            }else{
                $nrsitufuncm = 1;
                $dtRescisao = null;
            }
            
            if($sucessaoVinc && isset($sucessaoVinc['cnpjEmpregAnt'])){
                $estrutAnterior = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $sucessaoVinc['cnpjEmpregAnt'], $nrtipoestrutlegal, $dtmescompetenc);
                $estrutAntgeren = $this->entityManager->getRepository(Repositories::ESTRUTURAH)->retornaEstruturaPorInscricaoTipoEstrutura($nrorg, $sucessaoVinc['cnpjEmpregAnt'], $nrtipoestrutlegal, $dtmescompetenc);
                if($estrutAnterior){
                    $estrutPosterior = $nrestrutlegal;
                    $nrestrutlegal = $estrutAnterior[0]->getNrestruturam();
                }
            }
            
            // insere vínculo
            $vinculo = $this->novoVinculo($nrPessoa, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), null, 1, $infoCeletista['tpAdmissao'], $nrvinculoempreg, $dtOpcaoFGTS, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), 
                                          DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $trabalhador['nmTrab'], null, null, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $dtmescompetenc, $nrsitufuncm, $nrcargo, $nrEscalaTrab, null, null, null, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $idremuneracao,
                                          $idTpPagamento, $nrestrutlegal, $nrestrutgeren, 1, 'UNICO', $nrfuncao, null, $nrtpmovtransfm, $dtfimcontrdetermin, $nrestrutsind, 'N', $nrorg, $dtRescisao, null, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $vinculo['matricula'], 
                                          null, null, null);
            $vinculo[0]->setCdmatricula($vinculo[0]->getNrvinculom());
            array_push($mensagens, $this->msgSuccess . ' Número do vínculo criado: '.$vinculo[0]->getNrvinculom().'.');
            //array_push($mensagens, 'Vínculo '.$vinculo[0]->getNrvinculom().': Inserir movimentação para uma estrutura gerencial.');
            
            // insere altesalario
            $alteSalario = $this->novaAlteSalario($nrorg, $vinculo[0]->getNrvinculom(), DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), 1, 1, $remuneracao["vrSalFx"], $idTipoSalario, 1, $observacaoSalario, null, null, null);
            
            // insere movimentacao legal
            if($nrestrutlegal){
                $movimLegal = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $nrestrutlegal, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $nrtipoestrutlegal, $nrtpmovtransfm, null, null, 0, null, null);
                $movimgeren = $this->novaMovimentacao($nrorg, 2, $vinculo[0]->getNrvinculom(), $nrestrutgeren, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $nrtipoestrutgeren, $nrtpmovtransfm, null, null, 0, null, null);
                if(!empty($estrutPosterior)){
                    $dtfimmoviment = $this->alterDateFormat($sucessaoVinc['dtTransf']);
                    $movimLegalsaida = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $estrutPosterior, DateUtil::getDataDeString($dtfimmoviment), $nrtipoestrutlegal, 9, null, null, 0, DateUtil::getDataDeString($dtfimmoviment), $sucessaoVinc['observacao']);
                    //$movimLegalgeren = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $estrutPosterior, DateUtil::getDataDeString($dtfimmoviment), $nrtipoestrutlegal, 9, null, null, 0, DateUtil::getDataDeString($dtfimmoviment), $sucessaoVinc['observacao']);
                    $movimLegalentrada = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $estrutPosterior, DateUtil::adicionaIntervalo($dtfimmoviment, 1, DateUtil::DIA), $nrtipoestrutlegal, 8, null, null, 0, null, $sucessaoVinc['observacao']);
                    //$movimLegalengeren = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $estrutPosterior, DateUtil::adicionaIntervalo($dtfimmoviment, 1, DateUtil::DIA), $nrtipoestrutlegal, 8, null, null, 0, null, $sucessaoVinc['observacao']);
                    
                    $vinculoh = $vinculo[1];
                    $vinculoh->setDtmescompetenc(DateUtil::truncateData(DateUtil::getPrimeiroDiaDoMes(DateUtil::getDataDeString($dtfimmoviment, DateUtil::FORMATO_BRASILEIRO, true))));
                    $vinculoh->setNrvinculoh(\HCM\Util\NovoCodigo::geraCodigo($this->nrorg, 'GPE_VINCULOH', 1, 12, true));
                    $vinculoh->setNrestrutlegal($estrutPosterior);
                    
                    $this->entityManager->persist($movimLegalsaida);
                    $this->entityManager->persist($movimLegalentrada);
                    $this->entityManager->persist($vinculoh);
                    $this->entityManager->flush();
                    
                }
            }else{
                array_push($mensagens, 'Vínculo '.$vinculo[0]->getNrvinculom().': Não foi possível cadastrar uma movimentação com a estrutura legal de CNPJ '.$nrinsc[0].'.');
            }
            
            // insere movimentacao sindical
            if($nrestrutsind){
                $movimSind = $this->novaMovimentacao($nrorg, 1, $vinculo[0]->getNrvinculom(), $nrestrutsind, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), 10, $nrtpmovtransfm, null, null, 0, null, null);
            }else{
                array_push($mensagens, 'Vínculo '.$vinculo[0]->getNrvinculom().': Não foi possível cadastrar uma movimentação com a estrutura sindical de CNPJ '.$infoCeletista['cnpjSindCategProf'].'.');
            }
            
            // insere altesitufunc
            $situFuncional = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 1, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), null, null, null, null, null, null, null, null, null, null);
            
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
            
            if($desligamento){
                $situFuncional->setDtfimsitufunc(DateUtil::subtraiIntervalo($dtRescisao, 1, DateUtil::DIA));
                $situFuncDesligamento = $this->novaAltesitufunc($nrorg, $vinculo[0]->getNrvinculom(), 13, DateUtil::getDataDeString($dtRescisao), null, null, null, null, null, null, null, null, null, null);
            }
            
            // insere alteocupacao
            if($nrcargo){
                $ocupacaom = $this->entityManager->getRepository(Repositories::GPE_OCUPACAOM)->findOneBy(array('nrorg' => $nrorg, 'nrocupacaom' => $nrcargo));
                $alteOcupacao = $this->novaAlteOcupacao($nrorg, $vinculo[0]->getNrvinculom(), $nrcargo, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), $ocupacaom->getNrtipoocupacao(), 1, null, null, null, null);
            }
            
            // insere alteescala
            if($nrEscalaTrab){
                $nrturno = isset($escalaTrab['nrturno']) ? $escalaTrab['nrturno'] : null;
                $alteEscala = $this->novaAlteEscala($nrorg, $vinculo[0]->getNrvinculom(), $nrEscalaTrab, DateUtil::getDataDeString($dtAdmissao,DateUtil::FORMATO_BRASILEIRO,true), null, null, null, null, $nrturno, null);
            }else{
                array_push($mensagens, 'Vínculo '.$vinculo[0]->getNrvinculom().': Não foi encontrada escala para adicionar a alteração de escala de trabalho.');
            }
            
            if($dependentes){
                $dependentes = is_array($dependentes) ? $dependentes : [$dependentes]; 
                foreach($dependentes as $dependente){
                    $dependente = (array) $dependente;
                    
                    $dtNascimento = $this->alterDateFormat($dependente['dtNascto'], 2);
                    $tiporelaciona = $this->entityManager->getRepository(Repositories::TIPORELACIONA)->findOneBy(array('nrorg' => array($nrorg, $nrorgpadrao), 'cdesocial' => $dependente['tpDep']));
                    
                    if (is_object($tiporelaciona)) {
                        $parceiroDepend = $this->novoParcNegocio($nrorg, $dependente['nmDep'], $dependente['nmDep'], 'PESSOA', 'S', 'N', 'LIVRE', null, null, 'S', 'N'); 
                        $pessoaDepend = $this->novaPessoa($nrorg, $parceiroDepend->getNrparcnegocio(), $dtmescompetenc, $dependente['nmDep'], null, null, DateUtil::getDataDeString($dtNascimento)->setTime(0,0), null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                          null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                          null, null, null, null, null, null, null);
                        $relacionaparceiroDepend = $this->novoRelacionaparc($nrorg, $tiporelaciona->getNrtiporelaciona(), $nrParcnegocio, null, $parceiroDepend->getNrparcnegocio());
                        
                        if($dependente['tpDep'] == '03'){
                            // Imposto de Renda
                            $dependenteVincIRRF = $this->novoDepVinculo($nrorg, $pessoaDepend[0]->getNrpessoa(), 2, $vinculo[0]->getNrvinculom());
                            // Salário Família
                            $dependenteVincSF = $this->novoDepVinculo($nrorg, $pessoaDepend[0]->getNrpessoa(), 1, $vinculo[0]->getNrvinculom());
                            array_push($mensagens, 'Vínculo '.$vinculo[0]->getNrvinculom().': Verifique se as dependências estão corretas.(Pessoa dependende: '.$pessoaDepend[0]->getNrpessoa().')');
                        }
                    } else {
                        array_push($mensagens, 'Tipo de relacionamento não encontrado para o tipo de dependente do arquivo: '.$dependente['tpDep']);
                    }
                }
            }
            
            return array('status' => true,  
                         'messages' => $mensagens);
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtAdmissao' no arquivo).");
        }
    }
    
    private function novaEstruturaGerencial($nmestrutura, $nrInsc, $iniValid) {
        // Salva Parceiro de Negócio
        $parcnegocio = $this->novoParcNegocio($this->nrorg, $nmestrutura, $nmestrutura, 'ESTRUTURA', 'N', 'N',
                                        'CNPJ', $nrInsc, DateUtil::getDataDeString($iniValid,DateUtil::FORMATO_BRASILEIRO,true), 'S');
                                     
        // Salva Estrutura
        $estrutura = $this->novaEstrutura($this->nrtipoestrutgeren, $iniValid, 'S', 'N', $parcnegocio->getNrparcnegocio(), $nmestrutura, $nrInsc, null, null, null, null, null,
                                       null, null, null, null, null, null, null, null, null, null, $nmestrutura, null, null, null, null, null, null, null, null, null, null, null, $nmestrutura, $nmestrutura,
                                       null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
        
        return $estrutura[0]->getNrestruturam();
    }
    
}
