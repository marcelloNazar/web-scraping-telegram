#!/usr/bin/env python3
"""
Teste específico para verificar se o parsing das categorizações foi corrigido
"""

import sys
sys.path.append('./src')

def test_parsing_fix():
    """Testa se o parsing robusto resolve os problemas identificados"""
    
    print("🧪 TESTANDO CORREÇÃO DO PARSING DE CATEGORIZAÇÕES")
    print("="*60)
    
    # Importar função atualizada
    from utils.google_sheets import GoogleSheetsLoader
    
    loader = GoogleSheetsLoader()
    
    # Testar exemplos problemáticos do log
    test_cases = [
        "Direita_FTB: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'Bolsonarista', 'National'],",
        "acorrente: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'Bolsonarista', 'National'],",
        "jornalgeopolitico: ['Pol', 'Brasil', 'Debate', 'General', 'General', 'Ancap', 'None', 'National'],",
        "misogilandia: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'Red Pill', 'None', 'National'],",
        "historiaearqueologia: ['Pol', 'Brasil', 'Debate', 'General', 'Conservative', 'General', 'None', 'National'],",
        "clmbrasil: ['Pol', 'Brasil', 'News', 'General', 'Conservative', 'General', 'None', 'National'],",
        "avoztrabalhadora: ['Pol', 'Brasil', 'News', 'Left', 'Progressive', 'General', 'None', 'National'],",
        "brasilverdeoliva: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'None', 'National'],",
        "piadasepolitica: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'Red Pill', 'None', 'National'],",
        "COMANDOSbr: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'None', 'National'],",
        "memepolitico: ['Pol', 'Brasil', 'Meme', 'Left', 'Progressive', 'General', 'None', 'National'],",
        "redpillarena: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'Red Pill', 'None', 'National'],",
        "requuiao132022: ['Pol', 'Brasil', 'Personality', 'Left', 'Progressive', 'General', 'Lulista/Petista', 'National'],",
        "resistenciabrasilgrupo: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'None', 'National'],",
        "rolecomunista: ['Pol', 'Brasil', 'Debate', 'Left', 'Progressive', 'Socialist / Communist', 'None', 'National'],",
        "selvabrasiloficiall: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'None', 'National'],",
        "sssempreee: ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'Bolsonarista', 'National'],"
    ]
    
    print(f"🔍 Testando {len(test_cases)} casos problemáticos...")
    
    successful_parses = 0
    failed_parses = 0
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📋 Teste {i+1}: {test_case[:50]}...")
        
        # Tentar fazer parse
        username, categorization = loader.parse_categorization_column(test_case)
        
        if username and categorization:
            successful_parses += 1
            print(f"   ✅ Sucesso: {username}")
            print(f"      Project: {categorization.get('group_project')}")
            print(f"      Spectrum: {categorization.get('group_spectrum')}")
            print(f"      Stance: {categorization.get('group_stance')}")
            print(f"      Basis: {categorization.get('group_basis')}")
        else:
            failed_parses += 1
            print(f"   ❌ Falhou")
    
    print(f"\n📊 RESULTADOS DO TESTE:")
    print(f"   ✅ Sucessos: {successful_parses}/{len(test_cases)}")
    print(f"   ❌ Falhas: {failed_parses}/{len(test_cases)}")
    
    if successful_parses == len(test_cases):
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"✅ Parsing robusto está funcionando perfeitamente")
        return True
    elif successful_parses > 0:
        print(f"\n⚠️ Parsing parcialmente corrigido")
        print(f"📈 Taxa de sucesso: {(successful_parses/len(test_cases))*100:.1f}%")
        return False
    else:
        print(f"\n❌ Parsing ainda não está funcionando")
        return False


def test_full_integration():
    """Testa integração completa com o novo parsing"""
    
    print(f"\n🔄 TESTANDO INTEGRAÇÃO COMPLETA...")
    print("="*40)
    
    try:
        from utils.google_sheets import load_groups_with_categorizations
        
        # Carregar grupos com parsing atualizado
        groups_categorizations = load_groups_with_categorizations()
        
        if groups_categorizations:
            total_groups = len(groups_categorizations)
            
            # Contar grupos com categorização estruturada vs fallback
            structured_count = 0
            fallback_count = 0
            
            for username, data in groups_categorizations.items():
                # Verificar se tem categorização estruturada (não é fallback)
                if data.get('group_project') not in ['OTHER', 'Pol'] or data.get('group_spectrum') != 'General':
                    structured_count += 1
                else:
                    fallback_count += 1
            
            print(f"📊 Grupos carregados: {total_groups}")
            print(f"📈 Com categorização estruturada: {structured_count}")
            print(f"📉 Com fallback: {fallback_count}")
            
            if structured_count > 0:
                print(f"✅ Parsing está funcionando! {structured_count} grupos categorizados")
                
                # Mostrar exemplo
                for username, data in list(groups_categorizations.items())[:3]:
                    if data.get('group_project') != 'OTHER':
                        print(f"\n📋 Exemplo: {username}")
                        print(f"   Project: {data.get('group_project')}")
                        print(f"   Country: {data.get('group_country')}")
                        print(f"   Format: {data.get('group_format')}")
                        print(f"   Spectrum: {data.get('group_spectrum')}")
                        print(f"   Stance: {data.get('group_stance')}")
                        break
                
                return True
            else:
                print(f"⚠️ Nenhum grupo com categorização estruturada encontrado")
                return False
        else:
            print(f"❌ Nenhum grupo carregado")
            return False
            
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False


if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE CORREÇÃO DO PARSING")
    print("="*60)
    
    # Teste 1: Parsing dos casos problemáticos
    parsing_ok = test_parsing_fix()
    
    # Teste 2: Integração completa
    integration_ok = test_full_integration()
    
    print(f"\n" + "="*60)
    print(f"🏁 RESULTADO FINAL")
    print("="*60)
    
    if parsing_ok and integration_ok:
        print(f"🎉 CORREÇÃO BEM-SUCEDIDA!")
        print(f"✅ Parsing robusto: FUNCIONANDO")
        print(f"✅ Integração: FUNCIONANDO")
        print(f"\n🚀 PRONTO PARA USO EM PRODUÇÃO!")
    elif parsing_ok:
        print(f"⚠️ Parsing corrigido, mas integração com problemas")
    elif integration_ok:
        print(f"⚠️ Integração ok, mas parsing ainda com problemas")
    else:
        print(f"❌ Correção não foi bem-sucedida")
        print(f"📝 Pode ser necessário verificar formato da planilha")
    
    print("="*60)
