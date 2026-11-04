using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class RulesPage:Page {public RulesPage(){InitializeComponent();DataContext=App.State;}void AddRule(object sender,RoutedEventArgs e)=>App.State.AddRule();}
