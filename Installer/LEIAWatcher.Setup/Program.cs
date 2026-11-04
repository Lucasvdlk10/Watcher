using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
// Windows-only offline installer launcher: no privilege escalation and no network.
// It invokes a verified PowerShell installer beside the packaged Publish directory.
var root=AppContext.BaseDirectory;
var ps=Path.Combine(root,"install.ps1");
if(!File.Exists(ps)||!File.Exists(Path.Combine(root,"Publish","LEIAWatcher.App.exe"))){MessageBox.Show("Arquivos de instalação ausentes. Instalação cancelada.","LEIA Watcher 4");return 2;}
if(MessageBox.Show("Instalar LEIA Watcher 4? O motor Python 3.0 permanece intacto.","LEIA Watcher 4",MessageBoxButtons.OKCancel)!=DialogResult.OK)return 1;
var p=Process.Start(new ProcessStartInfo("powershell.exe") {UseShellExecute=false,Arguments="-NoProfile -ExecutionPolicy Bypass -File \""+ps+"\"",WorkingDirectory=root});
if(p==null)return 3;p.WaitForExit();MessageBox.Show(p.ExitCode==0?"Instalação concluída. Verifique o atalho do Watcher 4.":"Instalação não concluída. Consulte o log no diretório local.","LEIA Watcher 4");return p.ExitCode;
