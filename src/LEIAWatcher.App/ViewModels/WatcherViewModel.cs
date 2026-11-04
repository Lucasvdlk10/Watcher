using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
using System.Text.Json;
using System.Windows.Input;
using LEIAWatcher.Domain;
using LEIAWatcher.Ipc;
namespace LEIAWatcher.App.ViewModels;

public sealed class AsyncAction : ICommand {
 readonly Func<Task> action; readonly Func<bool>? guard; bool running;
 public AsyncAction(Func<Task> action,Func<bool>? guard=null){this.action=action;this.guard=guard;}
 public event EventHandler? CanExecuteChanged;
 public bool CanExecute(object? p)=>!running&&(guard?.Invoke()??true);
 public async void Execute(object? p){if(!CanExecute(p))return;running=true;CanExecuteChanged?.Invoke(this,EventArgs.Empty);try{await action();}finally{running=false;CanExecuteChanged?.Invoke(this,EventArgs.Empty);}}
}
public sealed class RootChoice {public string Name{get;set;}=""; public string Id{get;set;}=""; public JsonElement Json{get;set;} }
public sealed class DayBar {public string Day{get;set;}="";public double Height{get;set;}=4;public int Count{get;set;} }

public sealed class WatcherViewModel : Observable {
 BridgeClient? client;
 CancellationTokenSource? searchDelay;
 string message="Conectando ao motor local...",connection="Conectando",search="",newFolderPath="",newFolderName="",addMode="TRACK_ONLY",addProfile="TYPE",filterStatus="",filterExtension="",filterOrigin="",rulesFallback="Outros",ruleSteps="type";
 int filePage=0;bool activateFolder,confirmMovements,looseFolders;
 int totalFiles,currentFiles,legacyFiles,pending,undoEligible;
 RootChoice? selectedRoot;
 public string Message{get=>message;set=>Set(ref message,value);} public string ConnectionLabel{get=>connection;set=>Set(ref connection,value);}
 public string Search{get=>search;set {if(Set(ref search,value)){searchDelay?.Cancel();searchDelay=new CancellationTokenSource();var token=searchDelay.Token;_ = DebouncedSearchAsync(token);}}}
 public int TotalFiles{get=>totalFiles;set=>Set(ref totalFiles,value);}public int CurrentFiles{get=>currentFiles;set=>Set(ref currentFiles,value);}public int LegacyFiles{get=>legacyFiles;set=>Set(ref legacyFiles,value);} public int Pending{get=>pending;set=>Set(ref pending,value);} public int UndoEligible{get=>undoEligible;set=>Set(ref undoEligible,value);}
 public string NewFolderPath{get=>newFolderPath;set=>Set(ref newFolderPath,value);} public string NewFolderName{get=>newFolderName;set=>Set(ref newFolderName,value);}
 public string AddMode{get=>addMode;set{if(Set(ref addMode,value))Changed(nameof(IsOrganize));}}public bool IsOrganize=>AddMode=="ORGANIZE";
 public string AddProfile{get=>addProfile;set=>Set(ref addProfile,value);}public bool ActivateFolder{get=>activateFolder;set=>Set(ref activateFolder,value);}public bool ConfirmMovements{get=>confirmMovements;set=>Set(ref confirmMovements,value);}public bool LooseFolders{get=>looseFolders;set=>Set(ref looseFolders,value);}
 public string FilterStatus{get=>filterStatus;set=>Set(ref filterStatus,value);} public string FilterExtension{get=>filterExtension;set=>Set(ref filterExtension,value);} public string FilterOrigin{get=>filterOrigin;set=>Set(ref filterOrigin,value);}
 public int FilePage{get=>filePage;set{if(Set(ref filePage,value))Changed(nameof(FilePageLabel));}}public string FilePageLabel=>$"Página {FilePage+1} · {FilesTotal} resultados";
 int filesTotal;public int FilesTotal{get=>filesTotal;set{if(Set(ref filesTotal,value))Changed(nameof(FilePageLabel));}}
 public string RulesFallback{get=>rulesFallback;set=>Set(ref rulesFallback,value);}public string RuleSteps{get=>ruleSteps;set=>Set(ref ruleSteps,value);}
 public RootChoice? SelectedRoot {get=>selectedRoot;set{if(Set(ref selectedRoot,value))ReadRules(value);}}
 public ObservableCollection<RootChoice> RootChoices{get;}=new();public ObservableCollection<RuleEntry> Rules{get;}=new();
 public ObservableCollection<WatcherRoot> WatchedRoots{get;}=new();public ObservableCollection<FileEntry> Files{get;}=new();
 public ObservableCollection<AuditEntry> Recent{get;}=new();public ObservableCollection<AuditEntry> History{get;}=new();public ObservableCollection<DayBar> Activity{get;}=new();
 public string HermesSummary=>"IPC local autenticado · API Hermes somente leitura · nenhum modelo de linguagem";
 public AsyncAction PreviewRulesCommand{get;} public AsyncAction RefreshCommand{get;} public AsyncAction AddRootCommand{get;} public AsyncAction ValidateRulesCommand{get;} public AsyncAction SaveRulesCommand{get;}
 public AsyncAction LoadFilesCommand{get;} public AsyncAction NextFilesCommand{get;} public AsyncAction PreviousFilesCommand{get;} public AsyncAction LoadHistoryCommand{get;} public AsyncAction ScanCommand{get;} public AsyncAction BackupCommand{get;} public AsyncAction UndoCommand{get;} public AsyncAction ExportCommand{get;}
 public WatcherViewModel(){
  PreviewRulesCommand=new(PreviewRulesAsync);RefreshCommand=new(RefreshAsync);AddRootCommand=new(AddRootAsync);ValidateRulesCommand=new(ValidateRulesAsync);SaveRulesCommand=new(SaveRulesAsync);
  LoadFilesCommand=new(LoadFilesAsync);NextFilesCommand=new(async()=>{FilePage++;await LoadFilesAsync();});PreviousFilesCommand=new(async()=>{FilePage=Math.Max(0,FilePage-1);await LoadFilesAsync();});LoadHistoryCommand=new(LoadHistoryAsync);
  ScanCommand=new(ScanSelectedAsync);BackupCommand=new(BackupAsync);UndoCommand=new(UndoAsync);ExportCommand=new(ExportAsync);
  LoadPreferences();
 }
 BridgeClient Bridge(){if(client is null){var loc=BridgeLocator.Locate(AppContext.BaseDirectory);client=new(loc.Python,loc.Bridge);}return client;}
 async Task<JsonElement> Call(string command,object? args=null,CancellationToken ct=default)=>await Bridge().CallAsync(command,args,ct);
 async Task Run(Func<Task> task){try{await task();}catch(Exception ex){Message=ex.Message;ConnectionLabel="Desconectado";}}
 public Task RefreshAsync()=>Run(async()=>{
  ConnectionLabel="Conectando";
  JsonElement ping=await Call("ensure_core");
  if(!JsonFields.Bool(ping,"no_llm")||JsonFields.Str(ping,"db")!="ok")throw new InvalidOperationException("Core sem integridade confirmada. Operações bloqueadas.");
  var snap=await Call("ui_snapshot");
  if(!JsonFields.Bool(snap,"no_llm"))throw new InvalidOperationException("O modo sem LLM não está ativo.");
  TotalFiles=JsonFields.Int(snap,"files_count");CurrentFiles=JsonFields.Int(snap,"current_files_count");LegacyFiles=JsonFields.Int(snap,"legacy_files_count");Pending=JsonFields.Int(snap,"pending");UndoEligible=JsonFields.Int(snap,"undo_eligible");
  WatchedRoots.Clear();foreach(var r in JsonFields.Array(snap,"roots").EnumerateArray())WatchedRoots.Add(new(JsonFields.Str(r,"root_id"),JsonFields.Str(r,"name"),JsonFields.Str(r,"canonical_path"),JsonFields.Str(r,"mode"),JsonFields.Str(r,"health"),JsonFields.Bool(r,"enabled")));
  Recent.Clear();foreach(var a in JsonFields.Array(snap,"recent").EnumerateArray())Recent.Add(new(){Date=JsonFields.Str(a,"occurred_at"),Event=JsonFields.Str(a,"action"),Outcome=JsonFields.Str(a,"outcome"),Detail=JsonFields.Str(a,"reason_code")});
  ConnectionLabel="Ativo · SQLite OK";Message=$"Core {JsonFields.Str(ping,"version")} · dados locais reais · {TotalFiles} arquivos";
  await LoadRootsInternal(); await LoadActivityInternal();
 });
 async Task LoadRootsInternal(){var roots=await Call("roots");var keep=SelectedRoot?.Id;RootChoices.Clear();foreach(var r in roots.EnumerateArray())RootChoices.Add(new(){Name=JsonFields.Str(r,"name"),Id=JsonFields.Str(r,"id"),Json=r.Clone()});SelectedRoot=RootChoices.FirstOrDefault(x=>x.Id==keep)??RootChoices.FirstOrDefault();}
 async Task LoadActivityInternal(){var resp=await Call("ui_list",new{entity="audit",page=0,limit=100,filters=new{}});var hist=new int[7];var labels=new string[7];for(int i=0;i<7;i++)labels[i]=DateTime.Today.AddDays(i-6).ToString("ddd",new CultureInfo("pt-BR"));foreach(var e in JsonFields.Array(resp,"items").EnumerateArray()){
   if(DateTime.TryParse(JsonFields.Str(e,"occurred_at"),out var at)){int age=(DateTime.Today-at.Date).Days;if(age>=0&&age<7)hist[6-age]++;}
  }var peak=Math.Max(1,hist.Max());Activity.Clear();for(int i=0;i<7;i++)Activity.Add(new(){Day=labels[i],Count=hist[i],Height=8+90.0*hist[i]/peak});}
 async Task DebouncedSearchAsync(CancellationToken token){try{await Task.Delay(260,token);FilePage=0;await LoadFilesAsync();}catch(OperationCanceledException){}}
 public Task LoadFilesAsync()=>Run(async()=>{
  var filters=new Dictionary<string,string>();if(!string.IsNullOrWhiteSpace(Search))filters["q"]=Search.Trim();if(!string.IsNullOrWhiteSpace(FilterStatus)&&FilterStatus!="Todos")filters["status"]=FilterStatus;
  if(!string.IsNullOrWhiteSpace(FilterExtension))filters["extension"]=FilterExtension.Trim().TrimStart('.');
  var data=await Call("ui_files_origin",new{origin=string.IsNullOrEmpty(FilterOrigin)?"Todos":FilterOrigin,page=FilePage,limit=40,filters});Files.Clear();FilesTotal=JsonFields.Int(data,"total");
  foreach(var e in JsonFields.Array(data,"items").EnumerateArray()){
   var state=JsonFields.Str(e,"status");var legacy=state=="LEGACY";

   Files.Add(new(){Name=JsonFields.Str(e,"filename"),Path=JsonFields.Str(e,"relative_path"),Extension=JsonFields.Str(e,"extension"),State=legacy?"Histórico anterior":state,Source=legacy?"Downloads anterior":"Watcher atual",Date=JsonFields.Str(e,"seen_at")});
  }Message=$"Catálogo unificado · {FilesTotal} encontrados · página {FilePage+1}";
 });
 public Task LoadHistoryAsync()=>Run(async()=>{var data=await Call("ui_list",new{entity="audit",page=0,limit=100,filters=new{}});History.Clear();foreach(var a in JsonFields.Array(data,"items").EnumerateArray())History.Add(new(){Date=JsonFields.Str(a,"occurred_at"),Event=JsonFields.Str(a,"action"),Outcome=JsonFields.Str(a,"outcome"),Detail=JsonFields.Str(a,"reason_code")});});
 public Task AddRootAsync()=>Run(async()=>{
  if(!Directory.Exists(NewFolderPath))throw new IOException("Escolha uma pasta existente antes de aplicar.");
  if(IsOrganize&&ActivateFolder&&!ConfirmMovements)throw new InvalidOperationException("Confirme explicitamente antes de ativar movimentações.");
  var args=new{path=NewFolderPath,name=NewFolderName,mode=AddMode,organization_profile=AddProfile,organize_loose_folders=LooseFolders,activate=IsOrganize&&ActivateFolder,confirmation=(IsOrganize&&ActivateFolder&&ConfirmMovements)?"I_CONFIRM_FILE_MOVES":""};
  await Call("add_root",args);Message="Pasta adicionada pelo core; configuração validada e auditada.";await RefreshAsync();
 });
 void ReadRules(RootChoice? choice){Rules.Clear();if(choice is null)return;var root=choice.Json;if(!root.TryGetProperty("ruleset",out var rs))return;RulesFallback=JsonFields.Str(rs,"fallback_folder","Outros");
  var steps=JsonFields.Array(rs,"path_steps").EnumerateArray().Select(x=>x.ToString());RuleSteps=string.Join(",",steps);
  foreach(var x in JsonFields.Array(rs,"rules").EnumerateArray()){
   string kind=JsonFields.Str(x,"kind","type");string values=kind switch{"type"=>Csv(x,"extensions"),"keyword"=>Csv(x,"keywords"),"source"=>Csv(x,"categories"),"size"=>JsonFields.Str(x,"min_bytes","0")+","+JsonFields.Str(x,"max_bytes"),_=>JsonFields.Str(x,"pattern","YYYY/MM")};
   Rules.Add(new(){Id=JsonFields.Str(x,"id"),Kind=kind,Values=values,Target=JsonFields.Str(x,"target","Outros"),Enabled=JsonFields.Bool(x,"enabled")});
  }
 }
 static string Csv(JsonElement x,string key)=>string.Join(", ",JsonFields.Array(x,key).EnumerateArray().Select(y=>y.ToString()));
 public void AddRule()=>Rules.Add(new RuleEntry{Kind="type",Target="Outros",Values=".pdf"});
 public void RemoveRule(RuleEntry? r){if(r!=null)Rules.Remove(r);}
 object RulesPayload(bool confirmed)=>new{root_id=SelectedRoot?.Id??"",rows=Rules.Select(x=>new{x.Id,kind=x.Kind,values=x.Values,target=x.Target,enabled=x.Enabled}).Select(x=>new{id=x.Id,x.kind,x.values,x.target,x.enabled}).ToArray(),steps=RuleSteps.Split(',',StringSplitOptions.RemoveEmptyEntries|StringSplitOptions.TrimEntries),fallback=RulesFallback,confirmed};
 public Task PreviewRulesAsync()=>Run(async()=>{if(SelectedRoot==null)throw new InvalidOperationException("Escolha uma pasta");var x=await Call("preview",new{root_id=SelectedRoot.Id,limit=40});Message="Simulação de regras atualmente salvas concluída; nenhuma movimentação foi executada.";});
 public Task ValidateRulesAsync()=>Run(async()=>{var x=await Call("rules_validate",RulesPayload(false));Message=$"Regras validadas: {JsonFields.Int(x,"rules")}. Nenhum arquivo foi movido.";});
 public Task SaveRulesAsync()=>Run(async()=>{var x=await Call("rules_apply",RulesPayload(true));Message="Regras gravadas por transação nativa do Watcher; backup/auditoria preservados.";await RefreshAsync();});
 public Task ScanSelectedAsync()=>Run(async()=>{if(SelectedRoot==null)throw new InvalidOperationException("Selecione uma pasta");await Call("scan",new{root_id=SelectedRoot.Id});Message="Varredura solicitada ao core Watcher.";});
 public Task BackupAsync()=>Run(async()=>{var r=await Call("backup");Message="Backup criado pelo core em " + JsonFields.Str(r,"path");});
 public Task UndoAsync()=>Run(async()=>{if(UndoEligible<1)throw new InvalidOperationException("Não há movimentações reversíveis");if(SelectedRoot==null)throw new InvalidOperationException("Selecione uma pasta");await Call("undo",new{root_id=SelectedRoot.Id,confirmed=true});Message="Undo solicitado e auditado pelo core.";await RefreshAsync();});
 public Task ExportAsync()=>Run(async()=>{var path=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"LEIA-Watcher-audit-"+DateTime.Now.ToString("yyyyMMdd-HHmm")+".csv");var r=await Call("export",new{kind="audit",path});Message="Histórico exportado: "+JsonFields.Str(r,"path");});
 public async Task PauseRootAsync(string rootId){await Run(async()=>{await Call("pause",new{root_id=rootId});await RefreshAsync();});}
 public async Task ResumeRootAsync(string rootId){await Run(async()=>{await Call("resume",new{root_id=rootId});await RefreshAsync();});}
 public string Theme{get;set;}="Escuro"; public string Density{get;set;}="Compacta"; public string Motion{get;set;}="Reduzida";
 public bool Notifications{get;set;}=false;public bool StartWithWindows{get;set;}=false;
 static string PrefsPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LEIA","Watcher","frontend-v4.json");
 void LoadPreferences(){try{if(!File.Exists(PrefsPath))return;using var d=JsonDocument.Parse(File.ReadAllText(PrefsPath));Theme=JsonFields.Str(d.RootElement,"Theme","Escuro");Density=JsonFields.Str(d.RootElement,"Density","Compacta");Motion=JsonFields.Str(d.RootElement,"Motion","Reduzida");Notifications=JsonFields.Bool(d.RootElement,"Notifications");StartWithWindows=JsonFields.Bool(d.RootElement,"StartWithWindows");}catch{} }
 public void SavePreferences(){Directory.CreateDirectory(Path.GetDirectoryName(PrefsPath)!);var tmp=PrefsPath+".tmp";File.WriteAllText(tmp,JsonSerializer.Serialize(new{Theme,Density,Motion,Notifications,StartWithWindows}));File.Move(tmp,PrefsPath,true);Message="Preferências locais salvas. Sem envio de telemetria.";}
}
