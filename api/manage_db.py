# manage_db.py

from api.app import app, db # Importa a instância do app e db
from api.models import Usuario # Importa o modelo Usuario

def set_user_role_script(user_id, new_role):
    """
    Define o papel (role) para um usuário específico.

    Args:
        user_id (int): O ID do usuário a ser modificado.
        new_role (str): O novo papel ('usuario', 'funcionario', 'admin').
    """
    if new_role not in ['usuario', 'funcionario', 'admin']:
        print(f"Erro: Papel inválido '{new_role}'. Use 'usuario', 'funcionario' ou 'admin'.")
        return

    with app.app_context(): # Garante que estamos no contexto da aplicação Flask
        usuario = Usuario.query.get(user_id)
        if not usuario:
            print(f"Erro: Usuário com ID {user_id} não encontrado.")
            return

        usuario.role = new_role
        db.session.commit()
        
        print(f"Sucesso: Usuário '{usuario.nome}' (ID: {user_id}) definido como papel: '{new_role}'.")

if __name__ == '__main__':
    # --- Exemplos de uso ---

    # Exemplo 1: Tornar o usuário com ID 1 em ADMIN
    #print("\n--- Exemplo 1: Tornando o Usuário 1 em ADMIN ---")
    set_user_role_script(1, 'admin') 

    # Exemplo 2: Tornar o usuário com ID 2 em FUNCIONÁRIO
    #print("\n--- Exemplo 2: Tornando o Usuário 2 em Funcionário ---")
    #set_user_role_script(2, 'funcionario')

    # Exemplo 3: Tornar o usuário com ID 3 em USUÁRIO COMUM
    #print("\n--- Exemplo 3: Tornando o Usuário 3 em Usuário Comum ---")
    #set_user_role_script(3, 'usuario')