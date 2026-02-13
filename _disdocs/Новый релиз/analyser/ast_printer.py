import qspexpr
from token_ import QspToken, QspTokenType

class AstPrinter(qspexpr.Visitor):

    def print(self, expr:qspexpr.QspExpr) -> str:
        return expr.accept(self)

    def visit_binary_expr(self, expr: qspexpr.QspBinary) -> str:
        return self.parent_he_size(expr.operator.lexeme,
                                expr.left, expr.right)

    def visit_grouping_expr(self, expr: qspexpr.QspGrouping) -> str:
        return self.parent_he_size("group",
                                expr.expression)

    def visit_literal_expr(self, expr: qspexpr.QspLiteral) -> str:
        if expr.value == None: return "nil"
        return str(expr.value)

    def visit_unary_expr(self, expr: qspexpr.QspUnary) -> str:
        return self.parent_he_size(expr.operator.lexeme, expr.right)

    def parent_he_size(self, name:str, *exprs:qspexpr.QspExpr) -> str:
        builder = []
        builder.append('(')
        builder.append(name)
        for expr in exprs:
            builder.append(" ")
            builder.append(expr.accept(self))
        builder.append(")")

        return ''.join(builder)

if __name__ == "__main__":
    expr = qspexpr.QspBinary(
        qspexpr.QspUnary(
            QspToken(QspTokenType.MINUS, "-", None, 1),
            qspexpr.QspLiteral(123)
        ),
        QspToken(QspTokenType.STAR, "*", None, 1),
        qspexpr.QspGrouping(
            qspexpr.QspLiteral(45.67)
        )
    )

    print(AstPrinter().print(expr))