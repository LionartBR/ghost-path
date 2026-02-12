# ExMA

**Explicit Modular Architecture**
**Manual de Desenvolvimento para a Era da Colaboração Humano-IA**

Versão 1.0
Janeiro 2026

---

# Sumário

# Parte I: Fundamentos

## O Que é ExMA?

ExMA (Explicit Modular Architecture) é uma arquitetura de software projetada especificamente para maximizar a eficácia da colaboração entre desenvolvedores humanos e assistentes de IA. Ela sintetiza décadas de pesquisa em compreensão de código, design de software e gerenciamento de complexidade sob uma nova lente: otimização para contexto limitado e raciocínio explícito.

A arquitetura não inventa conceitos novos — ela integra princípios estabelecidos de forma coerente, com um propósito unificador: criar código que tanto humanos quanto IAs possam navegar, entender e modificar com precisão.

## Por Que ExMA?

Pesquisas recentes demonstram que LLMs sofrem degradação dramática de performance conforme o contexto aumenta. Um benchmark de 2025 mostrou o Claude 3.5 Sonnet caindo de 29% para 3% de acurácia com contextos crescentes. Tarefas binárias como correção de bugs amplificam erros: pequenos equívocos cascateiam para falha completa.

Paradoxalmente, as mesmas práticas que melhoram a compreensão humana de código também melhoram a compreensão por LLMs. Investir em ExMA traz retorno duplo: código mais manutenível para humanos e mais efetivo para assistência de IA.

## Princípio Fundamental: Localidade Máxima

> Se a IA precisa de contexto externo para entender um trecho de código, esse trecho está mal projetado.

A IA trabalha melhor quando tudo que ela precisa está próximo e visível. Cada decisão arquitetural deve favorecer código que pode ser compreendido sem saltos entre dezenas de arquivos, sem rastrear heranças profundas, sem depender de convenções implícitas.

Este princípio guia todos os outros. Quando em dúvida sobre uma decisão de design, pergunte: isso aumenta ou diminui a localidade do código?

---

# Parte II: Os Dez Pilares

## 1. Vertical Slice Architecture

**O quê:** Organize código por feature ou caso de uso, não por camada técnica.

**Por quê:** A IA pode carregar uma feature inteira em contexto e entender o fluxo completo, do input ao output.

### Estrutura Tradicional (evitar)

```
src/controllers/chapter_controller.rs
src/services/chapter_service.rs
src/repositories/chapter_repository.rs
```

### Estrutura Vertical (preferir)

```
src/features/add_chapter/mod.rs
src/features/add_chapter/command.rs
src/features/add_chapter/handler.rs
src/features/add_chapter/tests.rs
```

### Benefícios Documentados

- Maior coesão: código relacionado vive junto
- Package-private scoping: visibilidade restrita ao módulo
- Deletion test: remover uma feature = deletar uma pasta
- Navegação simplificada para humanos e IAs

### Regra Prática

Se você precisa abrir mais de 3-4 arquivos para entender uma feature, refatore. A feature deve ser compreensível como uma unidade.

## 2. Functional Core, Imperative Shell

**O quê:** Separe radicalmente a lógica de negócio (pura, sem side effects) da infraestrutura (IO, banco, APIs).

**Por quê:** O core puro é o ambiente ideal para a IA — ela pode gerar, testar e refatorar sem mocks, sem setup, sem preocupação com estado externo.

### O Padrão Impureim Sandwich

Mark Seemann demonstrou que código bem estruturado segue o padrão: impuro → puro → impuro. Leia entrada (impuro), processe (puro), escreva saída (impuro).

### Estrutura de Diretórios

```
src/core/          # Puro: apenas transformações de dados
src/core/manuscript.rs
src/core/chapter.rs
src/shell/         # Impuro: IO, persistência, APIs
src/shell/persistence/
src/shell/api/
```

### Características do Core Puro

- Funções determinísticas: mesma entrada sempre produz mesma saída
- Sem dependências de IO ou estado externo
- Testável sem mocks ou setup complexo
- Paralelizável por natureza

### Regra Prática

Se uma função de domínio precisa de async ou recebe um repository como parâmetro, ela provavelmente deveria estar no shell, não no core.

## 3. Deep Modules

**O quê:** Favoreça módulos com interfaces simples que escondem implementação substancial.

**Por quê:** Módulos profundos mantêm código relacionado junto enquanto apresentam contratos claros. Módulos rasos fragmentam lógica e aumentam saltos de contexto.

### O Conceito de John Ousterhout

Em "A Philosophy of Software Design", Ousterhout introduz a métrica de profundidade: a razão entre funcionalidade fornecida e complexidade da interface. Módulos profundos oferecem muito através de pouco.

### Sintomas de Complexidade a Evitar

- **Change amplification:** mudanças simples requerem modificações em muitos lugares
- **Cognitive load:** desenvolvedores precisam manter muita informação em memória
- **Unknown unknowns:** não é óbvio o que precisa ser modificado

### Regra Prática

"Pull complexity downward" — puxe complexidade para dentro dos módulos em vez de expô-la através de interfaces. A IA deve poder usar o módulo sem entender sua implementação.

## 4. Tipos como Documentação

**O quê:** Use tipos ricos e específicos em vez de primitivos genéricos.

**Por quê:** Tipos são prompts embutidos no código. A IA infere intenção, validações e invariantes automaticamente pelos tipos.

### Comparação

Assinatura opaca (evitar):

```rust
fn process(text: String, start: usize, end: usize, flag: bool) -> String
```

Assinatura expressiva (preferir):

```rust
fn extract_selection(content: &SceneContent, selection: TextRange, mode: ExtractionMode) -> SelectedText
```

### Tipos que Comunicam

```rust
pub struct ChapterTitle(String);      // Não é qualquer string
pub struct WordCount(u32);            // Não é qualquer número
pub struct TextRange { start: Position, end: Position }

pub enum ExtractionMode {
    KeepFormatting,
    PlainText,
    MarkdownPreserving,
}

pub enum MergeError {
    IncompatibleStructure,
    ConflictingMetadata,
    EmptyChapter,
}
```

### Regra Prática

Se você precisa de um comentário para explicar o que um parâmetro significa, ele deveria ser um tipo. Tipos errados não compilam; comentários errados passam silenciosamente.

## 5. Intent-Revealing Structure

**O quê:** A estrutura do código deve comunicar o domínio do negócio, não o framework técnico.

**Por quê:** Quando a estrutura grita o domínio, tanto humanos quanto IAs entendem o propósito sem ler implementação.

### Screaming Architecture (Robert Martin)

Ao olhar a estrutura de diretórios de um sistema de saúde, você deveria ver: `patients/`, `appointments/`, `prescriptions/` — não: `controllers/`, `services/`, `repositories/`.

### Naming Conventions que Comunicam

- **Ports (Hexagonal):** `ForPlacingOrders`, `ForStoringUsers` — não `OrderService`, `UserRepository`
- **Events:** `OrderPlaced`, `PaymentReceived` — verbos no passado indicando fatos
- **Commands:** `PlaceOrder`, `ProcessPayment` — imperativos indicando intenção

### Beacons de Código

Pesquisa de eye-tracking mostra que programadores experientes usam "beacons" — padrões reconhecíveis que ativam esquemas mentais. Consistência em naming e estrutura cria beacons que aceleram compreensão.

### Regra Prática

Um desenvolvedor novo (ou uma IA) deveria poder descrever o que o sistema faz olhando apenas a estrutura de diretórios e nomes de arquivos.

## 6. Arquivos Pequenos e Completos

**O quê:** Mantenha arquivos entre 200-400 linhas. Cada arquivo deve ser compreensível isoladamente.

**Por quê:** Arquivos que cabem na janela de contexto permitem que a IA trabalhe com visão completa, não parcial.

### Características de um Bom Arquivo

- **Coeso:** trata de um único conceito ou responsabilidade
- **Auto-contido:** imports explícitos, sem dependência de contexto global
- **Completo:** inclui tipos, implementação e testes relacionados quando pequeno

### Sinais de que Precisa Dividir

- Mais de 400 linhas
- Múltiplos `impl` blocks para tipos diferentes
- Seções separadas por comentários como `// --- Helpers ---`
- Precisa de scroll para encontrar funções relacionadas

### Lost-in-the-Middle Problem

Pesquisa mostra que LLMs performam melhor quando informação crítica aparece no início ou fim do contexto. Arquivos menores eliminam este problema; quando necessário, coloque informação importante nas bordas.

### Regra Prática

A IA deve poder ler o arquivo inteiro e dizer "entendi o que isso faz" em uma frase.

## 7. Information Hiding Estratégico

**O quê:** Módulos devem esconder decisões de design propensas a mudança, não corresponder a passos de processamento.

**Por quê:** Encapsulamento bem feito contém mudanças. Encapsulamento excessivo esconde contexto que a IA precisa.

### O Critério de Parnas (1972)

David Parnas estabeleceu que módulos devem esconder _design decisions likely to change_. Isso oferece três benefícios:

- **Gerencial:** equipes separadas trabalham independentemente
- **Flexibilidade:** mudanças drásticas ficam contidas
- **Compreensibilidade:** o sistema pode ser estudado um módulo por vez

### Tensão com IA

Information hiding agressivo pode esconder contexto que ferramentas de IA precisam. A resolução: esconda detalhes de implementação de outros módulos, mas forneça interfaces explícitas com documentação rica para ferramentas de IA.

### Law of Demeter

"Only talk to your immediate friends." Um método deve apenas invocar métodos em: seu próprio objeto, parâmetros recebidos, objetos que ele cria, ou objetos componentes diretos. Isso reduz dependências ocultas.

### Regra Prática

Se trocar a implementação de um lado de uma fronteira exige mudanças no outro lado, o contrato está vazando detalhes.

## 8. ADRs e Documentação Inline

**O quê:** Documente decisões arquiteturais diretamente no código, próximo ao código afetado.

**Por quê:** A IA lê isso e entende o _porquê_, não só o _como_. Evita sugestões que quebram decisões intencionais.

### Formato de ADR Inline

```rust
// ADR: Usamos Event Sourcing para Manuscript
//
// Contexto: Precisamos de histórico completo para:
//   - Recurso de versões do manuscrito
//   - Análise de padrões de escrita
//   - Undo/redo ilimitado
//
// Consequências:
//   - Estado é derivado de eventos
//   - Queries podem precisar de projeções
//   - Eventos são imutáveis
pub struct Manuscript {
    id: ManuscriptId,
    events: Vec<ManuscriptEvent>,
}
```

### Living Documentation (Cyrille Martraire)

A maior parte do conhecimento que vale compartilhar já existe no sistema — em código, testes, histórico de versão. O foco deve ser extrair e surfacear esse conhecimento, não criar documentação separada que inevitavelmente diverge.

### O que Documentar

- Escolhas não-óbvias de design
- Trade-offs aceitos conscientemente
- Padrões específicos do projeto
- Razões para NÃO usar uma abordagem comum

### Regra Prática

Se você escolheu A em vez de B por uma razão específica, documente. A IA vai sugerir B eventualmente.

## 9. Testes como Especificação

**O quê:** Escreva testes que funcionam como documentação executável dos requisitos.

**Por quê:** A IA pode gerar testes como forma de entender requisitos, e usar testes existentes como especificação para implementações.

### Testes que Especificam

```rust
#[cfg(test)]
mod merge_chapters_spec {
    #[test]
    fn preserves_scene_order_from_both_chapters() { }

    #[test]
    fn combines_metadata_preferring_first_chapter() { }

    #[test]
    fn fails_when_chapters_have_conflicting_timelines() { }

    #[test]
    fn generates_merge_event_for_history() { }
}
```

### Padrão para Nomes de Teste

- Descrevem comportamento, não implementação
- Legíveis como frases em linguagem natural
- Especificam cenário e resultado esperado
- Evitam termos técnicos quando possível

### Regra Prática

Alguém deveria poder ler apenas os nomes dos testes e entender o que a feature faz. Os testes são a especificação viva do comportamento.

## 10. Contratos Explícitos nas Fronteiras

**O quê:** Defina interfaces/traits claras entre módulos. Nunca dependa de implementações concretas entre fronteiras.

**Por quê:** A IA pode implementar um lado do contrato sem conhecer o outro. Facilita mudanças isoladas.

### Definindo Contratos

```rust
// contracts/persistence.rs
pub trait ManuscriptRepository {
    async fn get(&self, id: ManuscriptId) -> Result<Manuscript, RepoError>;
    async fn save(&self, manuscript: Manuscript) -> Result<(), RepoError>;
    async fn list_by_author(&self, author: AuthorId) -> Result<Vec<Summary>, RepoError>;
}
```

### Dependency Rule (Clean Architecture)

Dependências de código-fonte devem apontar para estabilidade e abstração. Módulos internos (lógica de domínio) nunca devem referenciar módulos externos (infraestrutura).

### Fronteiras Típicas

- Core ↔ Persistência
- Core ↔ APIs externas
- Core ↔ UI/CLI
- Feature ↔ Feature (quando necessário comunicar)

### Command-Query Separation

Bertrand Meyer estabeleceu: cada método deve ou mudar estado (command) ou retornar dados (query), nunca ambos. Isso torna mudanças de estado visíveis no nível da assinatura.

### Regra Prática

Se trocar a implementação de um lado da fronteira exige mudanças no outro lado, o contrato está vazando detalhes de implementação.

---

# Parte III: Context Engineering para IA

## Princípios de Otimização de Contexto

Guidance da Anthropic (2025) para construção de agentes de IA revela que contexto deve ser tratado como recurso finito com retornos decrescentes.

### Minimal Viable Context

Encontre o menor conjunto de tokens de alto sinal que maximiza resultados desejados. Mais contexto nem sempre é melhor — há um ponto de inflexão onde ruído supera sinal.

### Estratégias de Compactação

- Resuma histórico de conversa ao aproximar limites de contexto
- Preserve decisões arquiteturais e issues não resolvidos
- Descarte outputs redundantes e detalhes de implementação já processados

### Notas Persistentes

Para tarefas de longo prazo, mantenha arquivos como `NOTES.md` ou `ARCHITECTURE.md` fora da janela de contexto mas acessíveis. A IA pode consultá-los quando necessário sem carregar sempre.

### Arquitetura de Sub-Agentes

Agentes especializados lidam com tarefas focadas com contextos limpos, retornando resumos condensados para agentes líderes. Isso mapeia bem para vertical slices: um agente por feature.

## Redundância Estratégica de Contexto

Para otimização de IA, repita informação importante (propósito do módulo, constraints chave) em documentação no nível do arquivo. Endereça o problema lost-in-the-middle colocando informação crítica nas bordas dos arquivos.

### Cabeçalho de Arquivo Padrão

```rust
//! # Chapter Management
//!
//! Este módulo gerencia a estrutura de capítulos dentro de manuscritos.
//!
//! ## Invariantes
//! - Capítulos sempre pertencem a exatamente um manuscrito
//! - A ordem de cenas é preservada em todas as operações
//! - Merge de capítulos gera evento para histórico
//!
//! ## Decisões de Design
//! - Event sourcing para suportar undo/redo (ver ADR-003)
```

---

# Parte IV: Anti-Patterns

## O Que Evitar

### Herança Profunda

A IA precisa rastrear múltiplas classes para entender comportamento. Cada nível adiciona contexto necessário. Prefira composição sobre herança.

### Magic e Convenção sobre Configuração

Frameworks que "adivinham" comportamento baseado em nomes ou localização de arquivos confundem a IA. O que parece conveniente para humanos experientes é opaco para assistentes de IA. Seja explícito.

### Metaprogramação Pesada

Macros complexas, reflection, geração de código em runtime são caixas pretas para a IA. Ela não consegue rastrear o que será gerado ou executado. Use com moderação extrema.

### Estado Global Implícito

Singletons, variáveis globais, contextos implícitos quebram a localidade. A IA não sabe o que está disponível sem varrer todo o codebase. Injete dependências explicitamente.

### God Objects

Arquivos ou structs que fazem tudo violam o princípio de localidade. A IA precisa carregar muito contexto para entender qualquer parte. Divida em partes coesas com responsabilidades claras.

### Dependências Circulares

Módulos que dependem mutuamente criam grafos de dependência que a IA precisa carregar inteiros. Quebre ciclos introduzindo abstrações ou reorganizando responsabilidades.

---

# Parte V: Aplicação Prática

## Checklist de Revisão

Ao criar ou revisar código, pergunte:

### Localidade

- [ ] A IA consegue entender esta feature lendo 3-4 arquivos?
- [ ] O arquivo cabe confortavelmente na janela de contexto (< 400 linhas)?
- [ ] Informação crítica está no início ou fim do arquivo?

### Separação

- [ ] A lógica de negócio está separada de IO?
- [ ] Funções de domínio são puras (mesma entrada → mesma saída)?
- [ ] Commands e Queries estão separados?

### Expressividade

- [ ] Os tipos comunicam intenção sem precisar de comentários?
- [ ] A estrutura de diretórios revela o domínio do negócio?
- [ ] Nomes de arquivos e funções usam linguagem do domínio?

### Documentação

- [ ] Decisões não-óbvias estão documentadas com ADRs inline?
- [ ] Os testes descrevem comportamento como especificação?
- [ ] O propósito do módulo está claro no cabeçalho?

### Contratos

- [ ] Fronteiras entre módulos têm interfaces explícitas?
- [ ] Dependências apontam para abstração/estabilidade?
- [ ] É possível trocar implementações sem afetar contratos?

## Métricas de Saúde

| Categoria    | Métrica                     | Alvo    | Ferramenta                |
| ------------ | --------------------------- | ------- | ------------------------- |
| Complexidade | Ciclomática por função      | < 10    | clippy, complexity-report |
| Complexidade | Profundidade de aninhamento | < 4     | clippy                    |
| Tamanho      | Linhas por arquivo          | 200-400 | tokei, cloc               |
| Tamanho      | Linhas por função           | < 50    | clippy                    |
| Acoplamento  | Dependências por módulo     | < 7     | cargo-modules             |
| Acoplamento  | Fan-out (imports)           | < 10    | análise manual            |
| Cobertura    | Testes de domínio           | > 80%   | tarpaulin, coverage       |
| Documentação | ADRs por decisão            | 100%    | análise manual            |

| Métrica                     | Limite Recomendado | Razão                       |
| --------------------------- | ------------------ | --------------------------- |
| Complexidade ciclomática    | < 10 por função    | Limita caminhos de execução |
| Profundidade de aninhamento | < 4 níveis         | Reduz carga cognitiva       |
| Comprimento de linha        | < 120 caracteres   | Melhora legibilidade        |
| Tamanho de arquivo          | 200-400 linhas     | Cabe na janela de contexto  |

## Workflow de Desenvolvimento

### 1. Antes de Começar

- Identifique a feature/vertical slice afetada
- Revise ADRs existentes relacionados
- Verifique se há testes especificando comportamento esperado

### 2. Durante o Desenvolvimento

- Mantenha funções de domínio puras no core
- Use tipos específicos para comunicar intenção
- Documente decisões não-óbvias inline
- Escreva testes como especificação antes ou junto com implementação

### 3. Antes de Commit

- Verifique métricas de complexidade
- Confirme que arquivos estão dentro do limite de tamanho
- Revise se ADRs necessários foram adicionados
- Execute testes para confirmar especificações

### 4. Code Review

- Use o checklist de revisão
- Verifique se a IA conseguiria entender a mudança isoladamente
- Confirme que contratos nas fronteiras estão preservados

---

# Parte VI: Referências

## Livros Fundamentais

- "A Philosophy of Software Design" — John Ousterhout (deep modules, complexity)
- "Clean Architecture" — Robert C. Martin (dependency rule, screaming architecture)
- "Domain-Driven Design" — Eric Evans (ubiquitous language, bounded contexts)
- "Living Documentation" — Cyrille Martraire (documentation as code)

## Papers Acadêmicos

- "On the Criteria To Be Used in Decomposing Systems into Modules" — David Parnas, 1972
- "Learning a Metric for Code Readability" — Buse & Weimer, IEEE TSE 2010
- "Cognitive Dimensions of Notations" — Green & Petre
- "No Silver Bullet" — Fred Brooks, 1986
- "LongCodeBench: Evaluating Coding LLMs at 1M Context Windows" — arXiv 2025

## Talks e Screencasts

- "Boundaries" — Gary Bernhardt (Functional Core, Imperative Shell)
- "Functional architecture - The pits of success" — Mark Seemann
- "Effective Context Engineering for AI Agents" — Anthropic Engineering, 2025

## Padrões Arquiteturais

- Vertical Slice Architecture — Jimmy Bogard
- Hexagonal Architecture / Ports and Adapters — Alistair Cockburn
- Architecture Decision Records — Michael Nygard
- C4 Model — Simon Brown

---

_— ExMA v1.0 —_
_Explicit Modular Architecture_
_Para a era da colaboração humano-IA_
