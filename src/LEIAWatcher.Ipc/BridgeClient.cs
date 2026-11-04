using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using LEIAWatcher.Domain;

namespace LEIAWatcher.Ipc;
/// <summary>Persistent local stdio bridge. Only bundled Python adapter knows the authenticated IPC key.
/// JSON traffic stays local to the child process; no ports or web server added.</summary>
public sealed class BridgeClient : IAsyncDisposable {
 readonly SemaphoreSlim gate=new(1,1);
 readonly string python,bridge;
 Process? process;
 public BridgeClient(string pythonExecutable,string bridgeFile){python=pythonExecutable;bridge=bridgeFile;}
 public async Task<JsonElement> CallAsync(string command,object? args=null,CancellationToken ct=default){
  using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromSeconds(15));
  await gate.WaitAsync(timeout.Token).ConfigureAwait(false);
  try {
   if (process is null || process.HasExited) Start();
   var line=JsonSerializer.Serialize(new { command,args=args??new {} });
   await process!.StandardInput.WriteLineAsync(line.AsMemory(),timeout.Token).ConfigureAwait(false);
   await process.StandardInput.FlushAsync(timeout.Token).ConfigureAwait(false);
   var response=await process.StandardOutput.ReadLineAsync(timeout.Token).ConfigureAwait(false);
   if (string.IsNullOrEmpty(response)) throw new IOException("Ponte local indisponível.");
   using var parsed=JsonDocument.Parse(response);
   if (!JsonFields.Bool(parsed.RootElement,"ok")) throw new InvalidOperationException(JsonFields.Str(parsed.RootElement,"error","Erro de comunicação."));
   return parsed.RootElement.GetProperty("result").Clone();
  } catch (OperationCanceledException) {Reset();throw;} catch (IOException) {Reset();throw;} catch(JsonException) {Reset();throw;}
  finally {gate.Release();}
 }
 void Start() {
  Reset();
  var utf8NoBom=new UTF8Encoding(false);
  var psi=new ProcessStartInfo(python){UseShellExecute=false,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true,StandardOutputEncoding=utf8NoBom,StandardInputEncoding=utf8NoBom};
  psi.ArgumentList.Add("-u");psi.ArgumentList.Add(bridge);
  psi.Environment["PYTHONIOENCODING"]="utf-8";
  process=Process.Start(psi)??throw new IOException("Falha ao iniciar ponte Python.");
 }
 void Reset(){if(process is null)return;try {if(!process.HasExited)process.Kill(entireProcessTree:true);}catch{} process.Dispose();process=null;}
 public ValueTask DisposeAsync(){Reset();gate.Dispose();return ValueTask.CompletedTask;}
}
public static class BridgeLocator {
 public static (string Python,string Bridge) Locate(string appBase) {
  var python=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","LEIAWatcher",".venv","Scripts","python.exe");
  if(!File.Exists(python)) throw new FileNotFoundException("Core Watcher V3 não instalado. Nenhuma alteração foi feita.",python);
  var bridge=Path.Combine(appBase,"Bridge","watcher_bridge.py");
  if(!File.Exists(bridge)) throw new FileNotFoundException("Adaptador local não encontrado.",bridge);
  return (python,bridge);
 }
}
