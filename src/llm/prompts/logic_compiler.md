Convert the following premises into canonical first-order logic.

Use ONLY the ontology symbols provided.

Ontology:
{
  {{ontologies}}
}

Premises:
{{premises}}

For each premise:
- first determine whether it is a FACT, RULE, or EXISTENTIAL statement
- then generate parser-safe first-order logic

Classification guidelines:

FACT:
- ground statement
- no variables
- no quantifiers
- no implication

RULE:
- general implication
- usually contains quantified variables
- usually expresses conditions or requirements

EXISTENTIAL:
- explicit existence claim
- statements like:
  - "there exists"
  - "some"
  - "at least one"

Generation rules:

- use nested quantifiers only
- never invent ontology symbols
- preserve ontology argument order exactly
- preserve predicate/function arity exactly
- use functions only for numeric values
- avoid unnecessary nesting
- keep formulas parser-safe

Remember:
- facts go into "facts"
- implications go into "rules"
- existential claims go into "existentials"

Return JSON only.