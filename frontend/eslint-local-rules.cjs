/**
 * Custom ESLint rules for enforcing semantic color usage
 * Prevents hardcoded Tailwind color classes in favor of theme-aware semantic classes
 */

module.exports = {
  'no-hardcoded-colors': {
    meta: {
      type: 'problem',
      docs: {
        description: 'Disallow hardcoded Tailwind color classes, enforce semantic color usage',
        category: 'Best Practices',
        recommended: true,
      },
      messages: {
        hardcodedColor: 'Avoid hardcoded color "{{color}}". Use semantic classes instead: {{suggestion}}',
      },
      schema: [],
      fixable: null,
    },
    create(context) {
      // Patterns to detect hardcoded colors (excluding dark: variants which are intentional)
      const colorPatterns = [
        /\b(bg|text|border)-(gray|slate|zinc|neutral|stone)-\d+\b(?!.*dark:)/,
        /\b(bg|text|border)-(red|rose)-\d+\b(?!.*dark:)/,
        /\b(bg|text|border)-(orange|amber|yellow)-\d+\b(?!.*dark:)/,
        /\b(bg|text|border)-(green|emerald|teal|lime)-\d+\b(?!.*dark:)/,
        /\b(bg|text|border)-(blue|sky|cyan|indigo)-\d+\b(?!.*dark:)/,
        /\b(bg|text|border)-(purple|violet|fuchsia|pink)-\d+\b(?!.*dark:)/,
      ];

      // Semantic alternatives based on use case
      const suggestions = {
        'gray': 'bg-muted, text-muted-foreground, border-border, or bg-background',
        'slate': 'bg-muted, text-muted-foreground, border-border',
        'zinc': 'bg-muted, text-muted-foreground, border-border',
        'neutral': 'bg-muted, text-muted-foreground, border-border',
        'stone': 'bg-muted, text-muted-foreground, border-border',
        'red': 'text-destructive, bg-destructive, bg-error-subtle, text-error, border-error',
        'rose': 'text-destructive, bg-destructive, bg-error-subtle',
        'orange': 'text-warning, bg-warning-subtle, border-warning',
        'amber': 'text-warning, bg-warning-subtle, border-warning',
        'yellow': 'text-warning, bg-warning-subtle, border-warning',
        'green': 'text-success, bg-success-subtle, bg-success-container, border-success',
        'emerald': 'text-success, bg-success-subtle, border-success',
        'teal': 'text-success, bg-success-subtle',
        'lime': 'text-success, bg-success-subtle',
        'blue': 'text-info, bg-info-subtle, border-info, text-primary, bg-primary',
        'sky': 'text-info, bg-info-subtle, text-primary',
        'cyan': 'text-info, bg-info-subtle',
        'indigo': 'text-primary, bg-primary/10',
        'purple': 'text-primary, bg-primary/10',
        'violet': 'text-primary, bg-primary/10',
        'fuchsia': 'text-primary, bg-primary/10',
        'pink': 'text-primary, bg-primary/10',
      };

      function checkClassString(node, value) {
        if (typeof value !== 'string') return;

        // Skip if this is a dark: variant (intentional)
        if (value.includes('dark:')) return;

        // Check against all color patterns
        for (const pattern of colorPatterns) {
          const matches = value.match(pattern);
          if (matches) {
            const fullMatch = matches[0];
            const colorName = matches[2]; // e.g., 'gray', 'blue', 'red'
            
            context.report({
              node,
              messageId: 'hardcodedColor',
              data: {
                color: fullMatch,
                suggestion: suggestions[colorName] || 'semantic color classes',
              },
            });
          }
        }
      }

      return {
        // Check JSX className attributes
        JSXAttribute(node) {
          if (node.name.name === 'className' && node.value) {
            if (node.value.type === 'Literal') {
              checkClassString(node, node.value.value);
            } else if (node.value.type === 'JSXExpressionContainer') {
              const expr = node.value.expression;
              
              // Handle string literals in expressions
              if (expr.type === 'Literal' && typeof expr.value === 'string') {
                checkClassString(node, expr.value);
              }
              
              // Handle template literals
              if (expr.type === 'TemplateLiteral') {
                expr.quasis.forEach(quasi => {
                  checkClassString(node, quasi.value.raw);
                });
              }
              
              // Handle conditional expressions (ternary)
              if (expr.type === 'ConditionalExpression') {
                if (expr.consequent.type === 'Literal') {
                  checkClassString(node, expr.consequent.value);
                }
                if (expr.alternate.type === 'Literal') {
                  checkClassString(node, expr.alternate.value);
                }
              }
            }
          }
        },
      };
    },
  },
};
