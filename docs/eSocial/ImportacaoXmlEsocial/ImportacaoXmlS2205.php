<?php

namespace HCM\Geral\Logic\ImportacaoXmlEsocial;

use HCM\Util\DateUtil;
use HCM\Util\Repositories;


class ImportacaoXmlS2205 extends ImportacaoXmlEvento {
    
    const NMEVENTO = 'S-2205';
    
    public function __construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml) {
        parent::__construct($nrorg, $nrorgpadrao, $dtcompetencia, $cdoperador, $xml);
    }
    
    
    public function importarXml() {
        $nrorg = $this->nrorg;
        $nrorgpadrao = $this->nrorgpadrao;
        $competencia = $this->dtcompetencia;
        
        $mensagens = array();
        
        $evtAltCadastral  = (array) $this->xml->evtAltCadastral;
        
        if($evtAltCadastral){
            $ideTrabalhador = isset($evtAltCadastral['ideTrabalhador']) ? (array) $evtAltCadastral['ideTrabalhador'] : null;
            $alteracao = (array) $evtAltCadastral['alteracao'];
            $dtAlteracao = $this->alterDateFormat($alteracao['dtAlteracao'], 2);
            $compAlteracao = DateUtil::getDataDeString($this->alterDateFormat($alteracao['dtAlteracao'], 1), DateUtil::FORMATO_BRASILEIRO, true);
            $dadosTrabalhador = (array) $alteracao['dadosTrabalhador'];
            
            $pessoa = $this->entityManager->getRepository(Repositories::GPE_PESSOA)->retornaPessoaCpf($nrorg, $dtAlteracao, $ideTrabalhador['cpfTrab']);
            
            if($pessoa){
                
                // dados pessoa
                $nascimento = isset($dadosTrabalhador['nascimento']) ? (array) $dadosTrabalhador['nascimento'] : null;
                $documentos = isset($dadosTrabalhador['documentos']) ? (array) $dadosTrabalhador['documentos'] : null;
                $nisTrab = isset($dadosTrabalhador['nisTrab']) ? $dadosTrabalhador['nisTrab'] : null;
                $endereco = isset($dadosTrabalhador['endereco']) ? (array) $dadosTrabalhador['endereco'] : null;
                $infoDeficiencia = isset($dadosTrabalhador['infoDeficiencia']) ? (array) $dadosTrabalhador['infoDeficiencia'] : null;
                $contato = isset($dadosTrabalhador['contato']) ? (array) $dadosTrabalhador['contato'] : null;
                $trabEstrangeiro = isset($dadosTrabalhador['trabEstrangeiro']) ? (array) $dadosTrabalhador['trabEstrangeiro'] : null;
                $estCiv = isset($dadosTrabalhador['estCiv']) ? $dadosTrabalhador['estCiv'] : null;
                $racaCor = isset($dadosTrabalhador['racaCor']) ? $dadosTrabalhador['racaCor'] : null;
                $grauInstr = isset($dadosTrabalhador['grauInstr']) ? $dadosTrabalhador['grauInstr'] : null;
                
                // documentos
                $ctps = isset($documentos['CTPS']) ? (array) $documentos['CTPS'] : null;
                $rg = isset($documentos['RG']) ? (array) $documentos['RG'] : null;
                $rne = isset($documentos['RNE']) ? (array) $documentos['RNE'] : null;
                $cnh = isset($documentos['CNH']) ? (array) $documentos['CNH'] : null;
                
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
                
                if(is_null($ctps)){
                    $ctps['nrCtps'] = null;
                    $ctps['serieCtps'] = null;
                    $ctps['ufCtps'] = null;
                }
                
                if(is_null($rg)){
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
                
                if(is_null($rne)){
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
                
                if(is_null($cnh)){
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
                
                if(is_null($trabEstrangeiro)){
                    $trabEstrangeiro['dtChegada'] = null;
                    $trabEstrangeiro['classTrabEstrang'] = null;
                }else{
                    if(isset($trabEstrangeiro['classTrabEstrang'])){
                        $classTrabEstrang = $this->entityManager->getRepository(Repositories::GPE_CLASSESTRANG)->findOneBy(array('cdesocial' => $trabEstrangeiro['classTrabEstrang']));
                        $trabEstrangeiro['classTrabEstrang'] = $classTrabEstrang->getNrclassestrang();
                    }
                }
                
                $pessoah = $this->entityManager->getRepository(Repositories::GPE_PESSOAH)->retornaHistoricoAtualPorPessoa($nrorg, $pessoa[0]['NRPESSOA'], $compAlteracao);
                
                if($pessoah->getDtmescompetenc() == $compAlteracao){
                    
                    list($primeiroNome, $meioNome, $ultimoNome) = self::decompoeNomePessoa($dadosTrabalhador['nmTrab']);
                    
                    $pessoah->setNmpessoa($dadosTrabalhador['nmTrab']);
                    $pessoah->setDsprinomepess($primeiroNome);
                    $pessoah->setDsnomemeiopess((strlen($meioNome)> 20) ? substr($meioNome, 0, 20) : $meioNome);
                    $pessoah->setDsultnomepess($ultimoNome);
                    $pessoah->setDtnascpessoa(DateUtil::getDataDeString($dtnascimento, DateUtil::FORMATO_BRASILEIRO, true));
                    $pessoah->setIdsexopessoa($dadosTrabalhador['sexo']);
                    $pessoah->setNrcondfispes($nrCondicaoFisica);
                    $pessoah->setNrctpspessoa($ctps['nrCtps']);
                    $pessoah->setNrseriectpspes($ctps['serieCtps']);
                    $pessoah->setSgufctpspes($ctps['ufCtps']);
                    $pessoah->setNrpispaseppes($nrPIS);
                    $pessoah->setCdestacivil($cdEstacivil);
                    $pessoah->setNrcarthabpes($cnh['nrRegCnh']);
                    $pessoah->setDthabcartpes(DateUtil::getDataDeString($cnh['dtExped'], DateUtil::FORMATO_BRASILEIRO, true));
                    $pessoah->setDtvalhabcartpes(DateUtil::getDataDeString($cnh['dtValid'], DateUtil::FORMATO_BRASILEIRO, true));
                    $pessoah->setDscateghabcart($cnh['categoriaCnh']);
                    // $pessoah->set($cnh['ufCnh']);
                    $pessoah->setNrracapessoa($raca->getNrracapessoa());
                    $pessoah->setCdpais($paisNascto->getCdpais());
                    $pessoah->setSgestado($ufNascto);
                    $pessoah->setCdmunicipio($municNascto);
                    $pessoah->setNrrgpessoa($rg['nrRg']);
                    $pessoah->setCdexrgpessoa($rg['orgaoEmissor']);
                    $pessoah->setDtexrgpessoa(DateUtil::getDataDeString($rg['dtExped'], DateUtil::FORMATO_BRASILEIRO, true));
                    $pessoah->setNrnacionalid($nrNacionalidade);
                    $pessoah->setNrgrauinstr($nrGrauinstr);
                    $pessoah->setNrdocuestrang($rne['nrRne']);
                    $pessoah->setNrclassestrang($trabEstrangeiro['classTrabEstrang']);
                    $pessoah->setDsexpdocestr($rne['orgaoEmissor']);
                    $pessoah->setDsexpdocestr(DateUtil::getDataDeString($trabEstrangeiro['dtChegada'], DateUtil::FORMATO_BRASILEIRO, true));
                    $pessoah->setIdcotapcd($infoCota);
                    $pessoah->setDsexpdocestr($nrnitpessoa);
                    
                    $this->entityManager->persist($pessoah);
                    $this->entityManager->flush();
                    
                }else{
                    $this->pessoaHistorico($nrorg, $pessoah->getNrpessoa(), $compAlteracao, $dadosTrabalhador['nmTrab'], $pessoah->getDsapelidopess(), $pessoah->getNrcertnascpes(), DateUtil::getDataDeString($dtnascimento, DateUtil::FORMATO_BRASILEIRO, true), $dadosTrabalhador['sexo'], 
                                           $nrCondicaoFisica, $pessoah->getNrcpfpessoa(), $ctps['nrCtps'], $ctps['serieCtps'], $ctps['ufCtps'], $pessoah->getDtctpspessoa(), $nrPIS, $pessoah->getDtinscpispasep(), $pessoah->getNrinscinsspes(), $pessoah->getNrinscisspes(), 
                                           $cdEstacivil, $pessoah->getNrcertcasapes(), $pessoah->getDtcasapessoa(), $pessoah->getIdisentituelei(), $pessoah->getNrtitueleipes(), $pessoah->getNrsecaeleipes(), $pessoah->getNrzonaeleipes(), $cnh['nrRegCnh'], 
                                           DateUtil::getDataDeString($cnh['dtExped'], DateUtil::FORMATO_BRASILEIRO, true), DateUtil::getDataDeString($cnh['dtValid'], DateUtil::FORMATO_BRASILEIRO, true), $cnh['categoriaCnh'], $cnh['ufCnh'], $pessoah->getNrcatmilitarpe(), 
                                           $pessoah->getNrcertresepes(), $pessoah->getDscategcertrese(), $pessoah->getDtcertresepes(), $pessoah->getCdexcertresepes(), $raca->getNrracapessoa(), $pessoah->getIdgrupsangupes(), $pessoah->getIdfatorrhpes(), $paisNascto->getCdpais(), 
                                           $ufNascto, $municNascto, $rg['nrRg'], $rg['orgaoEmissor'], $pessoah->getSgufrgpessoa(), $pessoah->getDslocalexrgpes(), DateUtil::getDataDeString($rg['dtExped'], DateUtil::FORMATO_BRASILEIRO, true),
                                           $nrNacionalidade, $nrGrauinstr, $pessoah->getDspronometrat(), $pessoah->getNranochegapais(), $rne['nrRne'], $pessoah->getIdpesnaturaliza(), $pessoah->getDtnaturalizapes(), $pessoah->getIdposvistoperm(),
                                           $pessoah->getDtpermavisto(), $pessoah->getNrconselhoreg(), $pessoah->getNrinscrconsreg(), $pessoah->getDtexconsreg(), $pessoah->getSgufconsreg(), $pessoah->getCdtpbaixapag(), $pessoah->getNrlivrocertnasc(), $pessoah->getNrfolhacertnasc(),
                                           $pessoah->getDscomplcertnasc(), $pessoah->getNrregctpspes(), $trabEstrangeiro['classTrabEstrang'], $rne['orgaoEmissor'], DateUtil::getDataDeString($trabEstrangeiro['dtChegada'], DateUtil::FORMATO_BRASILEIRO, true), $infoCota, 
                                           $nrnitpessoa);  
                }
                                       
                // dados endereço
                $enderecoBr = $this->entityManager->getRepository(Repositories::ENDERECOPARC)->findOneBy(array('cdpais' => '0055', 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'nrorg' => $nrorg));
                if(isset($endereco['brasil']) && empty($enderecoBr)){
                    $enderecoBrasil = (array) $endereco['brasil'];
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('cdmunicibge' => $enderecoBrasil['codMunic'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $tpLograd = $this->entityManager->getRepository(Repositories::LOGRADOURO)->findOneBy(array('cdesocial' => $enderecoBrasil['tpLograd'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    
                    $cdMunicipio = is_object($cidade) ? $cidade->getCdmunicipio() : null;
                    $cdLogradouro = is_object($tpLograd) ? $tpLograd->getCdlogradouro() : null;
                    
                    $enderecoBrasil = $this->novoEndereco($pessoa[0]['NRPARCNEGOCIO'], '0055', $enderecoBrasil['uf'], $cdMunicipio, $cdLogradouro, $enderecoBrasil['bairro'], 'PRINCIPAL', $enderecoBrasil['cep'], $enderecoBrasil['complemento'], 
                                                          $enderecoBrasil['nrLograd'], $enderecoBrasil['dscLograd'], null);
                    unset($cidade);
                    unset($tpLograd);
                }
                
                $enderecoEx = $this->entityManager->getRepository(Repositories::ENDERECOPARC)->retornaEnderecoParcExterior($pessoa[0]['NRPARCNEGOCIO'], $nrorg);
                if(isset($endereco['exterior']) && empty($enderecoEx)){
                    $enderecoExterior = (array) $endereco['exterior']; 
                    $pais = $this->entityManager->getRepository(Repositories::PAIS)->findOneBy(array('cdesocial' => $enderecoExterior['paisResid'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    $cidade = $this->entityManager->getRepository(Repositories::MUNICIPIO)->findOneBy(array('nmmunicipio' => $enderecoExterior['nmCid'], 'nrorg' => array($nrorg, $nrorgpadrao)));
                    
                    $cdPais = is_object($pais) ? $pais->getCdpais() : null;
                    $cdMunicipio = is_object($cidade) ? $cidade->getCdmunicipio() : null;
                    
                    $enderecoExterior = $this->novoEndereco($pessoa[0]['NRPARCNEGOCIO'], $cdPais, null, $cdMunicipio, null, $enderecoExterior['bairro'], 'EXTERIOR', $enderecoExterior['codPostal'], $enderecoExterior['complemento'], 
                                                            $enderecoExterior['nrLograd'], $enderecoExterior['dscLograd'], null);
                    unset($cidade);
                    unset($pais);
                }
                // dados pais
                $relacionaM = $this->entityManager->getRepository(Repositories::RELACIONAPARC)->findOneBy(array('nrorg' => $nrorg, 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'nrtiporelaciona' => 1));
                if(isset($nascimento['nmMae']) && $nascimento['nmMae'] && empty($relacionaM)){
                    $parceiroMae = $this->novoParcNegocio($nrorg, $nascimento['nmMae'], $nascimento['nmMae'], 'PESSOA', 'S', 'N', 'LIVRE', null, null, 'S', 'N'); 
                    $pessoaMae = $this->novaPessoa($nrorg, $parceiroMae->getNrparcnegocio(), $compAlteracao, $nascimento['nmMae'], null, null, null, 'F', null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                  null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
                    $relacionaMae = $this->novoRelacionaparc($nrorg, 1, $pessoa[0]['NRPARCNEGOCIO'], null, $parceiroMae->getNrparcnegocio());
                }
                
                $relacionaP = $this->entityManager->getRepository(Repositories::RELACIONAPARC)->findOneBy(array('nrorg' => $nrorg, 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'nrtiporelaciona' => 2));
                if(isset($nascimento['nmPai']) && $nascimento['nmPai'] && empty($relacionaP)){
                    $parceiroPai = $this->novoParcNegocio($nrorg, $nascimento['nmPai'], $nascimento['nmPai'], 'PESSOA', 'S', 'N', 'LIVRE', null, null, 'S', 'N'); 
                    $pessoaPai = $this->novaPessoa($nrorg, $parceiroPai->getNrparcnegocio(), $compAlteracao, $nascimento['nmPai'], null, null, null, 'M', null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, 
                                                  null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null);
                    $relacionaPai = $this->novoRelacionaparc($nrorg, 2, $pessoa[0]['NRPARCNEGOCIO'], null, $parceiroPai->getNrparcnegocio());
                }
                
                // daods contato
                if(!empty($contato)){
                    $arrayContato = [];
                    $comunicafonePrinc = $this->entityManager->getRepository(Repositories::COMUNICAPARC)->findOneBy(array('nrorg' => $nrorg, 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'cdformacomu' => '01'));
                    if(isset($contato['fonePrinc']) && empty($comunicafonePrinc)){
                        $fonePrinc['CDFORMACOMU'] = '01';
                        $fonePrinc['NRPARCNEGOCIO'] = $pessoa[0]['NRPARCNEGOCIO'];
                        
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
                    $comunicafoneAlternat = $this->entityManager->getRepository(Repositories::COMUNICAPARC)->findOneBy(array('nrorg' => $nrorg, 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'cdformacomu' => '02'));
                    if(isset($contato['foneAlternat']) && empty($comunicafoneAlternat)){
                        $foneAlternat['CDFORMACOMU'] = '02';
                        $foneAlternat['NRPARCNEGOCIO'] = $pessoa[0]['NRPARCNEGOCIO'];
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
                    $comunicaemailPrinc = $this->entityManager->getRepository(Repositories::COMUNICAPARC)->findOneBy(array('nrorg' => $nrorg, 'nrparcnegocio' => $pessoa[0]['NRPARCNEGOCIO'], 'cdformacomu' => '05'));
                    if(isset($contato['emailPrinc']) && empty($comunicaemailPrinc)){
                        
                        $emailPrinc['CDFORMACOMU'] = '05';
                        $emailPrinc['NRPARCNEGOCIO'] = $pessoa[0]['NRPARCNEGOCIO'];
                        $emailPrinc['CDPREFIXCOMUPARC'] = '';
                        $emailPrinc['CDCOMUNICAPARC'] = $contato['emailPrinc'];
                        
                        array_push($arrayContato, $emailPrinc);
                        unset($emailPrinc);
                    }
                    
                    if(!empty($arrayContato)){
                        $this->novasFormasComunica($arrayContato);
                    }
                }
                
                return array('status' => true,     
                             'messages' => [$this->msgSuccess . ' Número da pessoa atualizada: '.$pessoah->getNrpessoa()]);
            
            }else{
                return array('status' => false,     
                             'message' => "Não foi encontrada pessoa com o CPF ".$ideTrabalhador['cpfTrab'].".");    
            }
        }else{
            return array('status' => false,     
                         'message' => self::MSG_ERRO_XML . " (Ausência da tag 'evtAltCadastral' no arquivo).");
        }
    }
    
}
