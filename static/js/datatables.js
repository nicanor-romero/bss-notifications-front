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
        ordering: true,
        order: [[3, 'asc'], [1, 'asc']],
        columnDefs: [
            // Código Cliente
            {targets: 0, searchable: true, width: '5%', className: 'dt-right'},
            // Razón Social
            {targets: 1, searchable: true},
            // Teléfono
            {targets: 2, searchable: true, width: '8%'},
            // Fecha de factura
            {targets: 3, searchable: true, width: '5%'},
            // Monto total a pagar
            {targets: 4, searchable: false, width: '8%', className: 'dt-right'},
            // Monto pagado
            {targets: 5, searchable: false, width: '8%', className: 'dt-right'},
            // Saldo
            {targets: 6, searchable: false, width: '8%', className: 'dt-right'},
            // Estado
            {targets: 7, searchable: false, width: '8%', className: 'dt-right'},
            // Acciones
            {targets: 8, searchable: false, width: '20%', className: 'dt-right'},
        ],
        language: language_es
    }
  );
});
