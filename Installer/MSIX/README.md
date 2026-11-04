# MSIX (necessita Windows e certificado de assinatura)

O projeto principal está configurado como **unpackaged** para coexistir com a instalação Python V3; empacotar uma cópia MSIX exige identidade de pacote e assinatura. Não há .msix nesta entrega porque não há build Windows nem certificado, e um MSIX sem assinatura não é instalável.

Passos no Windows: criar um projeto Windows Application Packaging Project apontando para `LEIAWatcher.App`, conferir a identidade MSIX, provisionar os assets de `Assets/AppIcon`, assinar o pacote com certificado confiável e executar validação na máquina de destino. Não transforme simplesmente a pasta do app unpackaged em MSIX com manifest inventado.
