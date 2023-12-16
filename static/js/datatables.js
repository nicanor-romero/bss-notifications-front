// Call the dataTables jQuery plugin

var language_es = {
    "search": "Buscar",
    "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
    "lengthMenu": "Mostrar _MENU_ registros",
    "zeroRecords": "No se encontraron resultados",
    "emptyTable": "Ningún dato disponible en esta tabla",
    "paginate": {
        "first": "Primero",
        "last": "Último",
        "next": "Siguiente",
        "previous": "Anterior"
    },
    "decimal": ",",
}

$(document).ready(function() {
  $('#notificationsTable').DataTable(
    {
        paging: true,
        searching: true,
        scrollX: false,
        pageLength: 50,
        ordering: false,
        columnDefs: [
            {targets: 0, searchable: true},
            {targets: 1, searchable: true},
            {targets: 2, searchable: true},
            {targets: 3, searchable: false},
            {targets: 4, searchable: false},
            {targets: 5, searchable: false},
        ],
        language: language_es
    }
  );
});
