#include <iostream>
#include <string>

// Definición de la clase
class Persona {
public:
    // Atributos (características)
    std::string nombre;
    int edad;

    // Método (acción)
    void saludar() {
        std::cout << "Hola, me llamo " << nombre << " y tengo " << edad << " años." << std::endl;
    }
};

int main() {
    // Creación de un objeto de la clase Persona
    Persona persona1;

    // Asignación de valores a los atributos
    persona1.nombre = "Carlos";
    persona1.edad = 20;

    // Llamada al método
    persona1.saludar();

    return 0;
}
